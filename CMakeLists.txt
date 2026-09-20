cmake_minimum_required(VERSION 3.24)
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION.txt" JEV_VERSION LIMIT_COUNT 1)
project(JevWorkbench VERSION ${JEV_VERSION} LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.8 REQUIRED COMPONENTS Quick QuickControls2 Widgets)
qt_standard_project_setup(REQUIRES 6.8)
qt_add_executable(JevWorkbench WIN32 MACOSX_BUNDLE desktop/main.cpp desktop/Workbench.cpp desktop/Workbench.h)
qt_add_resources(JevWorkbench "app_icons"
    PREFIX "/icons"
    BASE "desktop/assets"
    FILES desktop/assets/jev-workbench.png)
if(WIN32)
    target_sources(JevWorkbench PRIVATE desktop/app.rc)
endif()
qt_add_qml_module(JevWorkbench URI JevWorkbench VERSION 1.0
    SOURCES desktop/SyntaxHighlighter.cpp desktop/SyntaxHighlighter.h
    QML_FILES desktop/ConnectionPanel.qml desktop/Main.qml desktop/EditorPane.qml desktop/BlockButton.qml desktop/ThemeComboBox.qml desktop/ThemeMenuItem.qml)
target_link_libraries(JevWorkbench PRIVATE Qt6::Quick Qt6::QuickControls2 Qt6::Widgets)
target_include_directories(JevWorkbench PRIVATE desktop)
target_compile_definitions(JevWorkbench PRIVATE JEV_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}" JEV_VERSION="${PROJECT_VERSION}")
set_target_properties(JevWorkbench PROPERTIES
    MACOSX_BUNDLE_GUI_IDENTIFIER "com.jevworkbench.desktop"
    MACOSX_BUNDLE_BUNDLE_NAME "Jev Workbench"
    MACOSX_BUNDLE_BUNDLE_VERSION "${PROJECT_VERSION}"
    MACOSX_BUNDLE_SHORT_VERSION_STRING "${PROJECT_VERSION}")
install(TARGETS JevWorkbench BUNDLE DESTINATION . RUNTIME DESTINATION .)
include(CTest)
if(BUILD_TESTING)
    qt_add_executable(highlighter_check tests/highlighter_check.cpp desktop/SyntaxHighlighter.cpp desktop/SyntaxHighlighter.h)
    target_include_directories(highlighter_check PRIVATE desktop)
    target_link_libraries(highlighter_check PRIVATE Qt6::Quick)
    add_test(NAME syntax_highlighting COMMAND highlighter_check)
endif()
