#include "SyntaxHighlighter.h"
#include <QTextDocument>

SyntaxHighlighter::SyntaxHighlighter(QObject *parent) : QSyntaxHighlighter(parent) {}

void SyntaxHighlighter::setTarget(QQuickTextDocument *value) {
    if (m_target == value) return;
    m_target = value;
    setDocument(value ? value->textDocument() : nullptr);
    emit targetChanged();
}
void SyntaxHighlighter::setLanguage(const QString &value) {
    if (m_language == value) return;
    m_language = value; rehighlight(); emit languageChanged();
}
void SyntaxHighlighter::setDark(bool value) {
    if (m_dark == value) return;
    m_dark = value; rehighlight(); emit darkChanged();
}
void SyntaxHighlighter::paint(int start, int length, const char *light, const char *dark, bool bold) {
    QTextCharFormat format;
    format.setForeground(QColor(m_dark ? dark : light));
    if (bold) format.setFontWeight(QFont::DemiBold);
    setFormat(start, length, format);
}

void SyntaxHighlighter::highlightBlock(const QString &text) {
    setCurrentBlockState(0);
    if (m_language == "json") highlightJson(text);
    else if (m_language == "markdown") highlightMarkdown(text);
    else highlightLog(text);
}

void SyntaxHighlighter::highlightJson(const QString &text) {
    int position = 0;
    while (position < text.size()) {
        const auto character = text[position];
        if (character == '"') {
            const int start = position++;
            bool closed = false;
            while (position < text.size()) {
                if (text[position] == '\\') { position = qMin(position + 2, int(text.size())); continue; }
                if (text[position++] == '"') { closed = true; break; }
            }
            int next = position;
            while (next < text.size() && text[next].isSpace()) ++next;
            bool key = closed && next < text.size() && text[next] == ':';
            if (key) paint(start, position - start, "#254cb2", "#a8baff", true);
            else paint(start, position - start, "#186342", "#9fd5ad");
        } else if (character.isDigit() || character == '-') {
            const int start = position++;
            while (position < text.size() && (text[position].isDigit() || QString(".eE+-").contains(text[position]))) ++position;
            paint(start, position - start, "#8a410d", "#f4bf89");
        } else if (character.isLetter()) {
            const int start = position++;
            while (position < text.size() && text[position].isLetterOrNumber()) ++position;
            auto word = text.mid(start, position - start);
            if (word == "true" || word == "false" || word == "null")
                paint(start, position - start, "#793e96", "#d8a9ef", true);
        } else {
            if (QString("{}[]:,").contains(character)) paint(position, 1, "#505466", "#b8bcc8");
            ++position;
        }
    }
}

void SyntaxHighlighter::highlightMarkdown(const QString &text) {
    const auto trimmed = text.trimmed();
    if (trimmed.startsWith("```")) {
        setCurrentBlockState(previousBlockState() == 1 ? 0 : 1);
        paint(0, text.size(), "#793e96", "#d8a9ef", true);
        return;
    }
    if (previousBlockState() == 1) {
        setCurrentBlockState(1);
        paint(0, text.size(), "#186342", "#9fd5ad");
        return;
    }
    int prefix = 0;
    while (prefix < text.size() && text[prefix].isSpace()) ++prefix;
    if (trimmed.startsWith('#')) {
        paint(prefix, text.size() - prefix, "#254cb2", "#a8baff", true);
        return;
    }
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("> "))
        paint(prefix, 1, "#793e96", "#d8a9ef", true);
    for (int position = 0; position < text.size(); ++position) {
        if (text[position] == '\\') { ++position; continue; }
        QString delimiter;
        if (text[position] == '`') delimiter = "`";
        else if (text.mid(position, 2) == "**") delimiter = "**";
        else continue;
        int end = text.indexOf(delimiter, position + delimiter.size());
        if (end < 0) continue;
        paint(position, end + delimiter.size() - position,
              delimiter == "`" ? "#186342" : "#793e96",
              delimiter == "`" ? "#9fd5ad" : "#d8a9ef", delimiter == "**");
        position = end + delimiter.size() - 1;
    }
}

void SyntaxHighlighter::highlightLog(const QString &text) {
    if (text.trimmed().startsWith('"') || text.trimmed().startsWith('{') || text.trimmed().startsWith('[')) {
        highlightJson(text);
        return;
    }
    int position = 0;
    while (position < text.size()) {
        if (!text[position].isLetter()) { ++position; continue; }
        const int start = position++;
        while (position < text.size() && text[position].isLetter()) ++position;
        auto word = text.mid(start, position - start).toLower();
        if (word == "passed" || word == "completed") paint(start, position - start, "#186342", "#9fd5ad", true);
        if (word == "failed" || word == "error") paint(start, position - start, "#a02732", "#ffadb5", true);
        if (word == "verification" || word == "status" || word == "model") paint(start, position - start, "#254cb2", "#a8baff", true);
    }
}
