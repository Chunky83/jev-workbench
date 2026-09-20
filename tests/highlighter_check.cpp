#include "SyntaxHighlighter.h"
#include <QGuiApplication>
#include <QTextBlock>
#include <QTextLayout>
#include <QTextDocument>
#include <iostream>

QColor colorAt(const QTextBlock &block, int position) {
    for (const auto &range : block.layout()->formats())
        if (position >= range.start && position < range.start + range.length)
            return range.format.foreground().color();
    return {};
}

int main(int argc, char **argv) {
    QGuiApplication application(argc, argv);
    QTextDocument document;
    SyntaxHighlighter highlighter;
    highlighter.setDocument(&document);
    const QString json = R"({"key": "escaped \"true\"", "number": -1.25e+2, "flag": false, "empty": null})";
    document.setPlainText(json);
    highlighter.rehighlight();
    const auto block = document.firstBlock();
    if (colorAt(block, json.indexOf("key")) != QColor("#254cb2")) return 1;
    if (colorAt(block, json.indexOf("true")) != QColor("#186342")) return 2;
    if (colorAt(block, json.indexOf("-1.25")) != QColor("#8a410d")) return 3;
    if (colorAt(block, json.indexOf("false")) != QColor("#793e96")) return 4;
    highlighter.setDark(true);
    if (colorAt(block, json.indexOf("key")) != QColor("#a8baff")) return 5;
    if (document.toPlainText() != json) return 6;
    highlighter.setLanguage("markdown");
    document.setPlainText("# Evidence\nUse **facts** and `IDs`.\n```json\n{}\n```\nNormal text");
    highlighter.rehighlight();
    if (document.findBlockByNumber(2).userState() != 1) return 7;
    if (document.findBlockByNumber(3).userState() != 1) return 8;
    if (document.findBlockByNumber(4).userState() != 0) return 9;
    highlighter.setLanguage("log");
    document.setPlainText("Verification: Passed\nStatus: Failed");
    highlighter.rehighlight();
    if (colorAt(document.firstBlock(), 14) != QColor("#9fd5ad")) return 10;
    if (colorAt(document.lastBlock(), 8) != QColor("#ffadb5")) return 11;
    std::cout << "JSON escaping, theme changes, unchanged text, Markdown fences, and log statuses passed.\n";
    return 0;
}
