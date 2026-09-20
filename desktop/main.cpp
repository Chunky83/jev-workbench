#include "Workbench.h"
#include <QApplication>
#include <QIcon>
#include <cstdio>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QQuickStyle>
#include <QJsonDocument>
#include <QJsonArray>
#include <QStandardPaths>
#include <QTimer>
#include <QQuickItem>
#include <QMouseEvent>
#include <QTemporaryDir>
#include <QFile>
#include <QDir>
#include <QElapsedTimer>
#include <QProcessEnvironment>

int main(int argc, char *argv[]) {
    QQuickStyle::setStyle("Basic");
    QApplication app(argc, argv);
    app.setWindowIcon(QIcon(":/icons/jev-workbench.png"));
    app.setOrganizationName("JevWorkbench");
    app.setApplicationName(app.arguments().contains("--local-preview") ? "Jev Workbench Preview" : "Jev Workbench");
    app.setApplicationVersion(JEV_VERSION);
    if (app.arguments().contains("--ui-smoke") || app.arguments().contains("--workflow-ui-smoke") || app.arguments().contains("--sharing-ui-smoke") || app.arguments().contains("--setup-ui-smoke") || app.arguments().contains("--diagnostics-ui-smoke") || app.arguments().contains("--inbox-ui-smoke")) QStandardPaths::setTestModeEnabled(true);
    Workbench workbench;
    if (app.arguments().contains("--smoke-test")) return workbench.smokeCheck() ? 0 : 1;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("workbench", &workbench);
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed, &app, [] { QCoreApplication::exit(1); }, Qt::QueuedConnection);
    engine.loadFromModule("JevWorkbench", "Main");
    auto arguments = app.arguments();
    bool reviewRequested = false;
    if (arguments.contains("--review-claude-setup")) {
        QObject::connect(&workbench, &Workbench::workflowChanged, &app, [&] {
            if (reviewRequested) return;
            reviewRequested = true;
            auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
            auto profiles = view["integration"].toObject()["profiles"].toArray();
            if (profiles.size() == 1 && profiles[0].toObject()["available"].toBool() && !profiles[0].toObject()["configured"].toBool()) {
                auto id = profiles[0].toObject()["id"].toString();
                QTimer::singleShot(150, &app, [&, id] { workbench.workflow("setup_review", QString::fromUtf8(QJsonDocument(QJsonObject{{"profile_id", id}}).toJson())); });
            }
        });
        QTimer::singleShot(250, &app, [&] { QMetaObject::invokeMethod(engine.rootObjects().value(0), "openConnections"); });
    }
    int sharingStage = 0;
    QTemporaryDir setupProfile;
    int setupStage = 0;
    QString setupFile;
    QProcess inboxSender;
    QTimer inboxSmokeTimer;
    QElapsedTimer inboxSmokeWait;
    QString inboxFirstCase, inboxSecondCase, inboxEditorFolder, inboxEditorText, inboxProposal;
    int inboxSmokeStage = 0;
    if (arguments.contains("--inbox-ui-smoke")) {
        // Every case, connector call, and approval uses Workbench's isolated
        // temporary test database. No installed assistant configuration is used.
        auto fail = [&](int code, const QString &message) {
            qWarning() << "Inbox UI smoke stage" << inboxSmokeStage << message;
            fprintf(stderr, "Inbox UI smoke stage %d: %s\n", inboxSmokeStage, qPrintable(message));
            fflush(stderr);
            inboxSmokeTimer.stop(); app.exit(code);
        };
        QObject::connect(&workbench, &Workbench::failed, &app,
                         [&, fail](const QString &message) { fail(70, message); });
        QObject::connect(&inboxSender, &QProcess::errorOccurred, &app,
                         [fail](QProcess::ProcessError) { fail(71, "External MCP sender could not start"); });
        QObject::connect(&app, &QCoreApplication::aboutToQuit, &inboxSender, [&] {
            if (inboxSender.state() != QProcess::NotRunning) {
                inboxSender.kill(); inboxSender.waitForFinished(1000);
            }
        });
        inboxSmokeTimer.setInterval(100);
        QObject::connect(&inboxSmokeTimer, &QTimer::timeout, &app, [&, fail] {
            if (workbench.busy()) return;
            auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
            auto panel = window ? window->findChild<QObject *>("connectionPanel") : nullptr;
            auto popup = window ? window->findChild<QObject *>("incomingPopup") : nullptr;
            auto editor = window ? window->findChild<QObject *>("INSTRUCTIONSEditor") : nullptr;
            if (!window || !panel || !popup || !editor) { fail(72, "Native controls unavailable"); return; }
            auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
            auto editorPreserved = [&] {
                return workbench.caseFolder() == inboxEditorFolder
                    && window->property("dirty").toBool()
                    && editor->property("text").toString() == inboxEditorText
                    && view["case"].toObject()["case_id"].toString() == inboxSecondCase;
            };
            auto capture = [&](const QString &flag) {
                auto index = arguments.indexOf(flag);
                return index < 0 || (index + 1 < arguments.size() && window->grabWindow().save(arguments[index + 1]));
            };
            if (inboxSmokeStage == 0) {
                if (!view.contains("demo_folder")) return;
                inboxFirstCase = view["case"].toObject()["case_id"].toString();
                inboxSmokeStage = 1;
                workbench.workflow("share", "{\"hosts\":[\"claude\"]}");
            } else if (inboxSmokeStage == 1) {
                if (view["case"].toObject()["shared_with"].toArray() != QJsonArray{"claude"}) {
                    fail(73, "First case was not shared with the test connector"); return;
                }
                inboxSmokeStage = 2; workbench.previewFixture();
            } else if (inboxSmokeStage == 2) {
                inboxSecondCase = view["case"].toObject()["case_id"].toString();
                if (inboxSecondCase == inboxFirstCase || !view.contains("demo_folder")) {
                    fail(74, "Second independent case not prepared"); return;
                }
                inboxEditorFolder = workbench.caseFolder();
                window->setProperty("guidedMode", false);
                inboxEditorText = editor->property("text").toString() + "\nUnsaved second-case editor text must survive incoming review.";
                editor->setProperty("text", inboxEditorText);
                QMetaObject::invokeMethod(panel, "close");
                if (!editorPreserved()) { fail(75, "Second case did not become dirty"); return; }
                auto command = QJsonDocument::fromJson(workbench.connectorCommand("claude").toUtf8()).object();
                auto environment = QProcessEnvironment::systemEnvironment();
                auto configured = command["env"].toObject();
                for (auto item = configured.begin(); item != configured.end(); ++item)
                    environment.insert(item.key(), item.value().toString());
                inboxSender.setProcessEnvironment(environment);
                inboxSender.setProgram(command["command"].toString());
                inboxSender.setArguments({QString(JEV_SOURCE_ROOT) + "/tests/inbox_sender.py",
                    QString::fromUtf8(QJsonDocument(command).toJson(QJsonDocument::Compact)), inboxFirstCase});
                inboxSmokeStage = 3; inboxSender.start();
            } else if (inboxSmokeStage == 3) {
                if (inboxSender.state() != QProcess::NotRunning) return;
                if (inboxProposal.isEmpty()) {
                    auto result = QJsonDocument::fromJson(inboxSender.readAllStandardOutput()).object();
                    if (inboxSender.exitCode() != 0 || result["case_id"].toString() != inboxFirstCase
                        || result["proposal_id"].toString().isEmpty()) {
                        qWarning() << inboxSender.readAllStandardError();
                        fail(76, "Real MCP submission failed"); return;
                    }
                    inboxProposal = result["proposal_id"].toString();
                }
                // Do not call refreshInbox: the production listener must deliver it.
                if (workbench.pendingCount() != 1 || !popup->property("opened").toBool()) return;
                auto items = QJsonDocument::fromJson(workbench.inboxView().toUtf8()).object()["proposals"].toArray();
                if (items[0].toObject()["case_id"].toString() != inboxFirstCase
                    || items[0].toObject()["proposal_id"].toString() != inboxProposal
                    || window->property("inboxNotificationCount").toInt() != 1 || !editorPreserved()) {
                    fail(77, "Notification selected the wrong case or changed the editor"); return;
                }
                if (!capture("--capture-inbox")) { fail(78, "Inbox screenshot failed"); return; }
                QMetaObject::invokeMethod(popup, "close");
                inboxSmokeWait.start(); inboxSmokeStage = 4;
            } else if (inboxSmokeStage == 4) {
                if (inboxSmokeWait.elapsed() < 4500) return;
                if (popup->property("visible").toBool() || window->property("inboxNotificationCount").toInt() != 1
                    || workbench.pendingCount() != 1 || !editorPreserved()) {
                    fail(79, "Unchanged polling repeated the notification or lost editor state"); return;
                }
                inboxSmokeStage = 5; workbench.reviewIncoming(inboxFirstCase, inboxProposal);
            } else if (inboxSmokeStage == 5) {
                auto review = QJsonDocument::fromJson(workbench.reviewView().toUtf8()).object();
                auto records = review["records"].toObject();
                auto proposals = records["proposal"].toArray();
                if (review["case"].toObject()["case_id"].toString() != inboxFirstCase
                    || review["proposal_id"].toString() != inboxProposal || proposals.size() != 1
                    || proposals[0].toObject()["id"].toString() != inboxProposal
                    || !records["approval"].toArray().isEmpty() || !records["run"].toArray().isEmpty()
                    || !records["outcome"].toArray().isEmpty() || !editorPreserved()) {
                    const auto flags = QString("case=%1 proposal=%2 count=%3 selected=%4 approvals=%5 runs=%6 outcomes=%7 folder=%8 dirty=%9 text=%10 editorcase=%11")
                        .arg(review["case"].toObject()["case_id"].toString() == inboxFirstCase)
                        .arg(review["proposal_id"].toString() == inboxProposal).arg(proposals.size())
                        .arg(!proposals.isEmpty() && proposals[0].toObject()["id"].toString() == inboxProposal)
                        .arg(records["approval"].toArray().size()).arg(records["run"].toArray().size())
                        .arg(records["outcome"].toArray().size()).arg(workbench.caseFolder() == inboxEditorFolder)
                        .arg(window->property("dirty").toBool()).arg(editor->property("text").toString() == inboxEditorText)
                        .arg(view["case"].toObject()["case_id"].toString() == inboxSecondCase);
                    fail(80, "Review is not exact or work ran before approval: " + flags); return;
                }
                auto button = window->findChild<QObject *>("approveProposal");
                if (!panel->property("reviewingIncoming").toBool() || !button || !button->property("enabled").toBool()) {
                    fail(81, "Incoming proposal cannot be reviewed while another case is dirty"); return;
                }
                inboxSmokeStage = 6; QMetaObject::invokeMethod(button, "clicked");
            } else if (inboxSmokeStage == 6) {
                auto review = QJsonDocument::fromJson(workbench.reviewView().toUtf8()).object();
                auto records = review["records"].toObject();
                auto outcomes = records["outcome"].toArray();
                auto approvals = records["approval"].toArray();
                auto runs = records["run"].toArray();
                if (outcomes.isEmpty()) { fail(82, "Approval did not refresh the incoming result"); return; }
                if (review["case"].toObject()["case_id"].toString() != inboxFirstCase
                    || approvals.size() != 1 || approvals[0].toObject()["proposal_id"].toString() != inboxProposal
                    || runs.size() != 1 || runs[0].toObject()["proposal_id"].toString() != inboxProposal
                    || outcomes[0].toObject()["run_id"].toString() != runs[0].toObject()["id"].toString()
                    || outcomes[0].toObject()["verification"].toObject()["status"].toString() != "passed"
                    || !editorPreserved()) { fail(83, "Wrong proposal ran or result/editor preservation failed"); return; }
                inboxSmokeWait.start(); inboxSmokeStage = 7;
            } else if (inboxSmokeStage == 7) {
                if (inboxSmokeWait.elapsed() < 2500 || workbench.pendingCount() != 0) return;
                auto button = window->findChild<QObject *>("approveProposal");
                if (window->property("inboxNotificationCount").toInt() != 1 || !editorPreserved()
                    || !button || button->property("enabled").toBool()
                    || button->property("text").toString() != "Already approved") {
                    fail(84, "Final inbox, replay protection, or editor preservation failed"); return;
                }
                auto result = QJsonDocument::fromJson(window->property("rawOutput").toString().toUtf8()).object();
                if (window->property("resultKind").toString() != "Assistant workflow"
                    || !window->property("summaryOutput").toString().contains("guest: HTTP 401")
                    || !window->property("summaryOutput").toString().contains(inboxFirstCase.right(8))
                    || result["case"].toObject()["case_id"].toString() != inboxFirstCase
                    || window->property("guidedMode").toBool()
                    || !window->property("collected").isNull()) {
                    fail(87, "Approval did not publish matching summary and raw results to the workspace"); return;
                }
                if (!capture("--capture")) { fail(85, "Result screenshot failed"); return; }
                inboxSmokeTimer.stop(); app.exit(0);
            }
        });
        QTimer::singleShot(100, &workbench, &Workbench::previewFixture);
        inboxSmokeTimer.start();
        QTimer::singleShot(60000, &app, [fail] { fail(86, "Automatic delivery walkthrough timed out"); });
    } else if (arguments.contains("--diagnostics-ui-smoke")) {
        QObject::connect(&workbench, &Workbench::failed, &app, [&](const QString &message) { qWarning() << message; app.exit(60); });
        QObject::connect(&workbench, &Workbench::workflowChanged, &app, [&] {
            QTimer::singleShot(150, &app, [&] {
                auto root = engine.rootObjects().value(0);
                auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
                if (setupStage == 0) {
                    setupStage++;
                    auto button = root->findChild<QObject *>("runDiagnostics");
                    if (!button || !button->property("enabled").toBool()) { app.exit(61); return; }
                    QMetaObject::invokeMethod(button, "clicked");
                } else if (setupStage == 1) {
                    if (view["diagnostic"].toObject()["status"].toString() != "passed" || !view["integration"].toObject()["activity"].toArray().isEmpty()) { app.exit(62); return; }
                    setupStage++; workbench.previewFixture();
                } else if (setupStage == 2) {
                    setupStage++;
                    auto button = root->findChild<QObject *>("approveProposal");
                    if (!button || !button->property("enabled").toBool()) { app.exit(63); return; }
                    QMetaObject::invokeMethod(button, "clicked");
                } else if (setupStage == 3) {
                    auto outcomes = view["records"].toObject()["outcome"].toArray();
                    if (outcomes.isEmpty() || outcomes[0].toObject()["verification"].toObject()["status"].toString() != "passed") { app.exit(64); return; }
                    setupStage++; QMetaObject::invokeMethod(root, "openActivity");
                } else {
                    auto events = view["activity"].toObject()["events"].toArray();
                    bool approval = false, outcome = false, diagnostic = false;
                    for (const auto &value : events) {
                        auto event = value.toObject();
                        approval = approval || event["operation"].toString() == "approval";
                        outcome = outcome || event["operation"].toString() == "outcome";
                        diagnostic = diagnostic || event["actor"].toString() == "diagnostic";
                    }
                    if (!approval || !outcome || !diagnostic) { app.exit(65); return; }
                    auto index = arguments.indexOf("--capture");
                    if (index >= 0 && index+1 < arguments.size()) qobject_cast<QQuickWindow *>(root)->grabWindow().save(arguments[index+1]);
                    app.exit(0);
                }
            });
        });
        QTimer::singleShot(300, &app, [&] { QMetaObject::invokeMethod(engine.rootObjects().value(0), "openActivity"); });
        QTimer::singleShot(30000, &app, [&] { app.exit(66); });
    } else if (arguments.contains("--setup-ui-smoke")) {
        // Never exercise automatic configuration against the user's installed profile.
        if (!setupProfile.isValid()) return 40;
        qputenv("APPDATA", (setupProfile.path() + "/Roaming").toUtf8());
        qputenv("LOCALAPPDATA", (setupProfile.path() + "/Local").toUtf8());
        QDir().mkpath(setupProfile.path() + "/Roaming/Claude");
        setupFile = setupProfile.path() + "/Roaming/Claude/claude_desktop_config.json";
        QFile original(setupFile);
        if (!original.open(QIODevice::WriteOnly)) return 41;
        original.write("{\"mcpServers\":{\"existing\":{\"command\":\"preserve-me\"}},\"theme\":\"dark\"}");
        original.close();
        QObject::connect(&workbench, &Workbench::failed, &app, [&](const QString &message) {
            qWarning() << message; app.exit(42);
        });
        QObject::connect(&workbench, &Workbench::workflowChanged, &app, [&] {
            QTimer::singleShot(150, &app, [&] {
                auto window = engine.rootObjects().value(0);
                auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
                auto integration = view["integration"].toObject();
                if (setupStage < 2) {
                    auto name = setupStage++ == 0 ? "reviewSetup" : "approveSetup";
                    auto button = window->findChild<QObject *>(name);
                    if (!button || !button->property("enabled").toBool()) { app.exit(43); return; }
                    QMetaObject::invokeMethod(button, "clicked");
                    return;
                }
                auto plan = integration["plan"].toObject();
                QFile actual(setupFile);
                if (!actual.open(QIODevice::ReadOnly)) { app.exit(44); return; }
                auto settings = QJsonDocument::fromJson(actual.readAll()).object();
                if (settings["theme"].toString() != "dark" || settings["mcpServers"].toObject()["existing"].toObject()["command"].toString() != "preserve-me"
                    || plan["state"].toString() != "applied" || !integration["activity"].toArray().isEmpty()
                    || !settings["mcpServers"].toObject().contains("jev-workbench")) { app.exit(45); return; }
                auto index = arguments.indexOf("--capture");
                if (index >= 0 && index + 1 < arguments.size()) qobject_cast<QQuickWindow *>(window)->grabWindow().save(arguments[index + 1]);
                app.exit(0);
            });
        });
        QTimer::singleShot(300, &app, [&] { QMetaObject::invokeMethod(engine.rootObjects().value(0), "openConnections"); });
        QTimer::singleShot(15000, &app, [&] { app.exit(46); });
    } else if (arguments.contains("--workflow-ui-smoke") || arguments.contains("--sharing-ui-smoke") || arguments.contains("--demo")) {
        bool testMode = arguments.contains("--workflow-ui-smoke") || arguments.contains("--sharing-ui-smoke");
        QObject::connect(&workbench, &Workbench::failed, &app, [&, testMode](const QString &message) {
            if (testMode) { fprintf(stderr, "%s\n", qPrintable(message)); app.exit(20); }
        });
        QObject::connect(&workbench, &Workbench::workflowChanged, &app, [&, testMode] {
            auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
            auto records = view["records"].toObject();
            if (records["proposal"].toArray().isEmpty()) return;
            if (view.contains("demo_folder"))
                QMetaObject::invokeMethod(engine.rootObjects().value(0), "reviewProposal");
            if (arguments.contains("--sharing-ui-smoke")) {
                if (sharingStage == 0) {
                    sharingStage = 1;
                    QTimer::singleShot(200, &app, [&] {
                        QMetaObject::invokeMethod(engine.rootObjects().value(0), "openConnections");
                    });
                } else if (sharingStage == 1) {
                    sharingStage = 2;
                    QTimer::singleShot(200, &app, [&] {
                        auto window = engine.rootObjects().value(0);
                        auto check = window->findChild<QObject *>("shareClaude");
                        auto button = window->findChild<QObject *>("shareSnapshot");
                        if (!check || !button) { app.exit(30); return; }
                        check->setProperty("checked", true);
                        if (!button->property("enabled").toBool()) { app.exit(31); return; }
                        QMetaObject::invokeMethod(button, "clicked");
                    });
                } else {
                    QTimer::singleShot(200, &app, [&] {
                        auto window = engine.rootObjects().value(0);
                        auto panel = window->findChild<QObject *>("connectionPanel");
                        auto feedback = window->findChild<QObject *>("sharingFeedback");
                        auto view = QJsonDocument::fromJson(workbench.workflowView().toUtf8()).object();
                        auto hosts = view["case"].toObject()["shared_with"].toArray();
                        if (!panel || panel->property("currentPage").toInt() != 0
                            || !feedback || !feedback->property("text").toString().contains("shared with claude")
                            || hosts != QJsonArray{"claude"}
                            || panel->property("currentProposalCount").toInt() != 0) { app.exit(32); return; }
                        auto index = arguments.indexOf("--capture");
                        if (index >= 0 && index + 1 < arguments.size())
                            qobject_cast<QQuickWindow *>(window)->grabWindow().save(arguments[index + 1]);
                        app.exit(0);
                    });
                }
                return;
            }
            if (!testMode) return;
            auto outcomes = records["outcome"].toArray();
            if (!outcomes.isEmpty()) {
                if (outcomes[0].toObject()["verification"].toObject()["status"].toString() != "passed") { app.exit(21); return; }
                QTimer::singleShot(300, &app, [&] {
                    auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
                    auto approvalButton = window->findChild<QObject *>("approveProposal");
                    auto feedback = window->findChild<QObject *>("approvalFeedback");
                    if (!approvalButton || approvalButton->property("enabled").toBool()
                        || approvalButton->property("text").toString() != "Already approved"
                        || !feedback || !feedback->property("text").toString().contains("already approved")) {
                        fprintf(stderr, "Completed proposal must explain why repeat approval is disabled.\n");
                        app.exit(25); return;
                    }
                    auto index = arguments.indexOf("--capture");
                    if (index >= 0 && index + 1 < arguments.size() && !window->grabWindow().save(arguments[index + 1])) { app.exit(22); return; }
                    app.exit(0);
                });
                return;
            }
            QTimer::singleShot(300, &app, [&] {
                auto button = engine.rootObjects().value(0)->findChild<QObject *>("approveProposal");
                if (!button || !button->property("enabled").toBool()) { qWarning() << "Approval button missing or disabled" << button << workbench.busy() << workbench.workflowView(); app.exit(23); return; }
                QMetaObject::invokeMethod(button, "clicked");
            });
        });
        QTimer::singleShot(100, &workbench, &Workbench::previewFixture);
        if (testMode) QTimer::singleShot(15000, &app, [&] { app.exit(24); });
    } else if (arguments.contains("--ui-smoke")) {
        auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
        if (!window) return 2;
        QObject::connect(&workbench, &Workbench::failed, &app, [&](const QString &message) {
            qWarning() << message; app.exit(3);
        });
        QObject::connect(&workbench, &Workbench::outputReady, &app, [&](const QString &text, const QString &kind) {
            if (kind != "run") return;
            auto result = QJsonDocument::fromJson(text.toUtf8()).object()["result"].toObject();
            if (result["verification"].toString() != "Passed") { app.exit(4); return; }
            QTimer::singleShot(200, &app, [&] {
                auto testedWindow = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
                if (!testedWindow->property("summaryOutput").toString().contains("PASSED")) { app.exit(5); return; }
                auto captureIndex = arguments.indexOf("--capture");
                if (captureIndex >= 0 && captureIndex + 1 < arguments.size()) {
                    if (!testedWindow->grabWindow().save(arguments[captureIndex + 1])) { app.exit(6); return; }
                }
                app.exit(0);
            });
        });
        QTimer::singleShot(400, &app, [&] {
            auto testedWindow = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
            auto editor = testedWindow->findChild<QObject *>("INSTRUCTIONSEditor");
            auto runButton = testedWindow->findChild<QObject *>("runButton");
            if (!editor || !runButton) { app.exit(7); return; }
            for (const auto &name : {"runButton", "runMode", "modelSelector"}) {
                auto control = testedWindow->findChild<QQuickItem *>(name);
                if (!control) { app.exit(12); return; }
                auto background = control->property("background").value<QObject *>();
                if (!background) { app.exit(12); return; }
                for (auto reason : {Qt::MouseFocusReason, Qt::TabFocusReason, Qt::BacktabFocusReason}) {
                    control->setFocus(false);
                    control->forceActiveFocus(reason);
                    QCoreApplication::processEvents();
                    auto border = background->property("border").value<QObject *>();
                    auto expectedWidth = reason == Qt::MouseFocusReason ? 2 : 3;
                    if (!border || border->property("width").toInt() != expectedWidth) {
                        qWarning() << "Incorrect focus outline:" << name << reason
                                   << control->hasActiveFocus() << control->property("visualFocus")
                                   << control->property("focusReason");
                        app.exit(13); return;
                    }
                }
                control->setFocus(false);
            }
            editor->setProperty("text", editor->property("text").toString() + "\nSmoke test edit.");
            if (!testedWindow->property("dirty").toBool()) { app.exit(8); return; }
            testedWindow->setProperty("expanded", 0);
            testedWindow->setProperty("expanded", -1);
            QMetaObject::invokeMethod(runButton, "clicked");
        });
        QTimer::singleShot(15000, &app, [&] { app.exit(9); });
    } else if (arguments.contains("--capture")) {
        if (arguments.contains("--capture-connections")) {
            QTimer::singleShot(400, &app, [&] {
                QMetaObject::invokeMethod(engine.rootObjects().value(0), "openConnections");
            });
        }
        if (arguments.contains("--capture-question")) {
            QTimer::singleShot(400, &app, [&] {
                auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
                auto button = window->findChild<QObject *>("questionButton");
                QMetaObject::invokeMethod(button, "clicked");
                QTimer::singleShot(150, &app, [&] {
                    auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
                    auto option = window->findChild<QQuickItem *>("scoreOption");
                    if (!option) { app.exit(11); return; }
                    auto position = option->mapToScene(QPointF(option->width() / 2, option->height() / 2));
                    QMouseEvent hover(QEvent::MouseMove, position, window->mapToGlobal(position.toPoint()), Qt::NoButton, Qt::NoButton, Qt::NoModifier);
                    QCoreApplication::sendEvent(window, &hover);
                });
            });
        }
        if (arguments.contains("--capture-dropdown") || arguments.contains("--capture-model")) {
            QTimer::singleShot(400, &app, [&] {
                auto name = arguments.contains("--capture-model") ? "modelSelector" : "runMode";
                auto control = engine.rootObjects().value(0)->findChild<QObject *>(name);
                auto popup = control ? control->property("popup").value<QObject *>() : nullptr;
                if (!popup) { app.exit(10); return; }
                QMetaObject::invokeMethod(popup, "open");
            });
        }
        auto index = arguments.indexOf("--capture");
        if (index + 1 < arguments.size()) {
            QTimer::singleShot(1200, &app, [&] {
                auto window = qobject_cast<QQuickWindow *>(engine.rootObjects().value(0));
                app.exit(window && window->grabWindow().save(arguments[index + 1]) ? 0 : 2);
            });
        }
    }
    return app.exec();
}
