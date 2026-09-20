#pragma once

#include <QSyntaxHighlighter>
#include <QQuickTextDocument>
#include <QPointer>
#include <QtQml/qqmlregistration.h>

// A small character scanner. No regular expressions and no document rewriting.
class SyntaxHighlighter : public QSyntaxHighlighter {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QQuickTextDocument *target READ target WRITE setTarget NOTIFY targetChanged)
    Q_PROPERTY(QString language READ language WRITE setLanguage NOTIFY languageChanged)
    Q_PROPERTY(bool dark READ dark WRITE setDark NOTIFY darkChanged)
public:
    explicit SyntaxHighlighter(QObject *parent = nullptr);
    QQuickTextDocument *target() const { return m_target; }
    void setTarget(QQuickTextDocument *value);
    QString language() const { return m_language; }
    void setLanguage(const QString &value);
    bool dark() const { return m_dark; }
    void setDark(bool value);
signals:
    void targetChanged();
    void languageChanged();
    void darkChanged();
protected:
    void highlightBlock(const QString &text) override;
private:
    void highlightJson(const QString &text);
    void highlightMarkdown(const QString &text);
    void highlightLog(const QString &text);
    void paint(int start, int length, const char *light, const char *dark, bool bold = false);
    QPointer<QQuickTextDocument> m_target;
    QString m_language = "json";
    bool m_dark = false;
};
