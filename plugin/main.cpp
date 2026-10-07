#include "notch.hpp"

#include <algorithm>

#include <hyprland/src/Compositor.hpp>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/desktop/view/Window.hpp>
#include <hyprland/src/event/EventBus.hpp>
#include <hyprland/src/render/Renderer.hpp>

APICALL EXPORT std::string PLUGIN_API_VERSION() {
    return HYPRLAND_API_VERSION;
}

static CNotch* notchOf(PHLWINDOW window) {
    for (auto& deco : window->m_windowDecorations)
        if (auto notch = dynamic_cast<CNotch*>(deco.get()))
            return notch;
    return nullptr;
}

static void frame(PHLWINDOW window) {
    if (!window->m_X11DoesntWantBorders && !notchOf(window))
        HyprlandAPI::addWindowDecoration(PHANDLE, window, makeUnique<CNotch>(window));
}

static void redrawAll() {
    for (auto& window : Desktop::windowState()->windows())
        if (auto notch = notchOf(window))
            notch->damageEntire();
}

APICALL EXPORT PLUGIN_DESCRIPTION_INFO PLUGIN_INIT(HANDLE handle) {
    PHANDLE = handle;

    if (__hyprland_api_get_hash() != std::string{__hyprland_api_get_client_hash()}) {
        HyprlandAPI::addNotification(PHANDLE, "[athanor] The notch was built for another Hyprland. Rebuild it with ./install.sh notch.", CHyprColor{0.82, 0.37, 0.26, 1.0}, 8000);
        throw std::runtime_error("[athanor] version mismatch");
    }

    using namespace Config::Values;
    config.active   = makeShared<CColorValue>("plugin:athanor:col.active", "focused window's rule and title", 0xffd49a3a);
    config.rule     = makeShared<CColorValue>("plugin:athanor:col.rule", "other windows' rule and title", 0xff8d7d65);
    config.bg       = makeShared<CColorValue>("plugin:athanor:col.bg", "behind the rules and the title", 0xff16120e);
    config.font     = makeShared<CStringValue>("plugin:athanor:font", "title font", "PxPlus IBM VGA 8x16");
    config.fontSize = makeShared<CIntValue>("plugin:athanor:font_size", "title size in pixels", 16, SIntValueOptions{.min = 6, .max = 64});
    for (SP<IValue> value : {SP<IValue>(config.active), SP<IValue>(config.rule), SP<IValue>(config.bg), SP<IValue>(config.font), SP<IValue>(config.fontSize)})
        HyprlandAPI::addConfigValueV2(PHANDLE, value);
    HyprlandAPI::reloadConfig();

    auto& events = Event::bus()->m_events;
    static auto onOpen       = events.window.open.listen([](PHLWINDOW w) { frame(w); });
    static auto onTitle      = events.window.title.listen([](PHLWINDOW w) {
        if (auto notch = notchOf(w))
            notch->damageEntire();
    });
    static auto onActive     = events.window.active.listen([](PHLWINDOW, Desktop::eFocusReason) { redrawAll(); });
    static auto onFullscreen = events.window.fullscreen.listen([](PHLWINDOW) { redrawAll(); });
    static auto onReload     = events.config.reloaded.listen([] { redrawAll(); });

    for (auto& window : Desktop::windowState()->windows())
        if (window->m_isMapped && !window->isHidden())
            frame(window);

    return {"athanor", "Window titles set into the border, and a double rule on the focused window.", "Script Wizards", "0.2.0"};
}

APICALL EXPORT void PLUGIN_EXIT() {
    g_pHyprRenderer->m_renderPass.removeAllOfType("CNotchPass");
}
