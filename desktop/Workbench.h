#pragma once

#include <QObject>
#include <QProcess>
#include <QJsonObject>
#include <QTimer>
#include <QTemporaryDir>

class Workbench : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString inboxView READ inboxView NOTIFY inboxChanged)
    Q_PROPERTY(QString reviewView READ reviewView NOTIFY reviewChanged)
    Q_PROPERTY(QString inboxStatus READ inboxStatus NOTIFY inboxChanged)
    Q_PROPERTY(int pendingCount READ pendingCount NOTIFY inboxChanged)
    Q_PROPERTY(QString workflowView READ workflowView NOTIFY workflowChanged)
    Q_PROPERTY(QString connectorStatus READ connectorStatus NOTIFY workflowChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(bool keyAvailable READ keyAvailable NOTIFY keyChanged)
    Q_PROPERTY(QString caseFolder READ caseFolder NOTIFY folderChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)
    Q_PROPERTY(QString theme READ theme WRITE setTheme NOTIFY themeChanged)
public:
    explicit Workbench(QObject *parent = nullptr);
    bool busy() const { return m_process.state() != QProcess::NotRunning; }
    bool keyAvailable() const;
    QString caseFolder() const { return m_folder; }
    QString status() const { return m_status; }
    QString theme() const { return m_theme; }
    void setTheme(const QString &value);
    QString workflowView() const { return m_workflowView; }
    QString connectorStatus() const { return m_connectorStatus; }
    QString inboxView() const { return m_inboxView; }
    QString reviewView() const { return m_reviewView; }
    QString inboxStatus() const { return m_inboxStatus; }
    int pendingCount() const;
    Q_INVOKABLE void refreshInbox();
    Q_INVOKABLE void notifyIncoming();
    Q_INVOKABLE void reviewIncoming(const QString &caseId, const QString &proposalId);
    Q_INVOKABLE void clearIncomingReview();
    Q_INVOKABLE void copyConnectionPrompt();
    Q_INVOKABLE void copyProposalPrompt();
    Q_INVOKABLE void previewFixture();
    Q_INVOKABLE void workflow(const QString &operation, const QString &parameters = "{}");
    Q_INVOKABLE QString connectorCommand(const QString &host) const;
    Q_INVOKABLE QString initialCase() const;
    Q_INVOKABLE void openCase();
    Q_INVOKABLE void newCase();
    Q_INVOKABLE void saveCase(const QString &document, bool saveAs);
    Q_INVOKABLE void evaluate(const QString &document, const QString &mode);
    Q_INVOKABLE void preview(const QString &document);
    Q_INVOKABLE void history();
    Q_INVOKABLE void cancel();
    Q_INVOKABLE void setApiKey(const QString &key);
    Q_INVOKABLE void showFolder();
    Q_INVOKABLE bool confirmDiscard();
    Q_INVOKABLE bool smokeCheck();
signals:
    void inboxChanged();
    void reviewChanged();
    void workflowChanged();
    void workflowRunFinished(QString view);
    void busyChanged();
    void keyChanged();
    void folderChanged();
    void statusChanged();
    void themeChanged();
    void caseLoaded(QString document);
    void saved();
    void outputReady(QString text, QString kind);
    void failed(QString text);
private:
    void logEvent(const QString &operation, const QString &status, const QString &error = "none");
    QString m_requestId, m_logOperation;
    void start(QJsonObject message);
    QJsonObject parseCase(const QString &document);
    void complete(int exitCode, QProcess::ExitStatus status);
    void setStatus(const QString &value);
    QString dataFolder() const;
    QString pythonPath() const;
    QStringList workerArguments() const;
    QString workerRoot() const;
    QTemporaryDir m_testData;
    QProcess m_process;
    QProcess m_inboxProcess;
    QTimer m_inboxTimer, m_inboxTimeout;
    QByteArray m_inboxOutput;
    QString m_inboxView = "{}", m_reviewView = "{}", m_inboxStatus = "Waiting for assistant updates";
    QTimer m_timeout;
    QByteArray m_output;
    QString m_folder, m_status = "Ready. Start with the local checks.", m_key, m_theme;
    QString m_action, m_pendingFolder;
    QString m_workflowView = "{}", m_connectorStatus = "Assistants: setup required | Jev allowance: off";
    QString m_workflowCase, m_workflowOperation;
    bool m_cancelled = false;
};
