#include "notch.hpp"

#include <algorithm>
#include <cmath>
#include <format>

#include <hyprland/src/Compositor.hpp>
#include <hyprland/src/desktop/state/FocusState.hpp>
#include <hyprland/src/desktop/view/Window.hpp>
#include <hyprland/src/managers/fullscreen/FullscreenController.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <hyprland/src/render/decorations/DecorationPositioner.hpp>

using namespace Render::GL;

constexpr double BAND  = 4;
constexpr double INSET = 14;
constexpr double PAD   = 6;
constexpr auto   EDGES = DECORATION_EDGE_TOP | DECORATION_EDGE_BOTTOM | DECORATION_EDGE_LEFT | DECORATION_EDGE_RIGHT;

static CHyprColor color(const SP<Config::Values::CColorValue>& value, float a) {
    CHyprColor c{static_cast<uint64_t>(value->value())};
    c.a *= a;
    return c;
}

static void outline(const CBox& box, double t, const CHyprColor& c) {
    g_pHyprOpenGL->renderRect({box.x, box.y, box.w, t}, c, {});
    g_pHyprOpenGL->renderRect({box.x, box.y + box.h - t, box.w, t}, c, {});
    g_pHyprOpenGL->renderRect({box.x, box.y + t, t, box.h - 2 * t}, c, {});
    g_pHyprOpenGL->renderRect({box.x + box.w - t, box.y + t, t, box.h - 2 * t}, c, {});
}

CNotch::CNotch(PHLWINDOW window) : IHyprWindowDecoration(window), m_window(window) {}

CNotch::~CNotch() {
    damageEntire();
}

SDecorationPositioningInfo CNotch::getPositioningInfo() {
    SDecorationPositioningInfo info;
    info.policy         = DECORATION_POSITION_STICKY;
    info.reserved       = true;
    info.priority       = 9990;
    info.edges          = EDGES;
    info.desiredExtents = {{BAND, BAND}, {BAND, BAND}};
    return info;
}

void CNotch::onPositioningReply(const SDecorationPositioningReply& reply) {
    m_assigned = reply.assignedGeometry;
}

eDecorationType CNotch::getDecorationType() {
    return DECORATION_CUSTOM;
}

uint64_t CNotch::getDecorationFlags() {
    return DECORATION_PART_OF_MAIN_WINDOW;
}

eDecorationLayer CNotch::getDecorationLayer() {
    return DECORATION_LAYER_OVER;
}

std::string CNotch::getDisplayName() {
    return "athanor-notch";
}

void CNotch::updateWindow(PHLWINDOW) {
    damageEntire();
}

CBox CNotch::frameBox() {
    const auto window    = m_window.lock();
    const auto workspace = window->m_workspace;
    const auto offset    = workspace && !window->m_pinned ? workspace->m_renderOffset->value() : Vector2D{};
    return m_assigned.copy().translate(g_pDecorationPositioner->getEdgeDefinedPoint(EDGES, window)).translate(window->m_floatingOffset + offset);
}

void CNotch::damageEntire() {
    if (validMapped(m_window))
        g_pHyprRenderer->damageBox(frameBox().expand(config.fontSize->value()));
}

bool CNotch::shown() {
    if (!validMapped(m_window))
        return false;
    const auto window = m_window.lock();
    return window->m_ruleApplicator->decorate().valueOrDefault() && !Fullscreen::controller()->isFullscreen(window);
}

void CNotch::draw(PHLMONITOR, float const& a) {
    if (shown())
        g_pHyprRenderer->m_renderPass.add(makeUnique<CNotchPass>(this, a));
}

void CNotch::drawPass(PHLMONITOR monitor, float a) {
    const auto   window = m_window.lock();
    const double scale  = monitor->m_scale;

    CBox         box = frameBox().translate(-monitor->m_position).scale(scale).round();
    if (box.w < 1 || box.h < 1)
        return;

    const bool focused    = Desktop::focusState()->window() == window;
    const auto inkSetting = focused ? config.active : config.rule;
    const auto ink        = color(inkSetting, a);
    const auto paper      = color(config.bg, a);
    const auto band       = std::round(BAND * scale);
    const auto line       = std::max(1.0, std::round(scale));

    g_pHyprOpenGL->scissor(nullptr);
    outline(box, band, paper);
    outline(box, line, ink);
    if (focused)
        outline(box.copy().expand(line - band), line, ink);

    const int px       = std::round(config.fontSize->value() * scale);
    const int inset    = std::round(INSET * scale);
    const int pad      = std::round(PAD * scale);
    const int maxWidth = box.w - 2 * inset - 2 * pad;
    if (window->m_title.empty() || window->m_group || maxWidth < px)
        return;

    const auto key = std::format("{}\n{}\n{}\n{}\n{:x}", window->m_title, px, maxWidth, config.font->value(), inkSetting->value());
    if (key != m_titleKey || !m_title) {
        m_title    = g_pHyprRenderer->renderText(window->m_title, color(inkSetting, 1), px, false, config.font->value(), maxWidth);
        m_titleKey = key;
    }
    if (!m_title)
        return;

    const auto size  = m_title->m_size;
    CBox       notch = {box.x + inset, box.y + std::round(band / 2 - size.y / 2), size.x + 2 * pad, size.y};
    g_pHyprOpenGL->renderRect(notch, paper, {});
    g_pHyprOpenGL->renderTexture(m_title, {notch.x + pad, notch.y, size.x, size.y}, {.a = a});
}

CNotchPass::CNotchPass(CNotch* notch, float a) : m_notch(notch), m_a(a) {}

std::vector<UP<IPassElement>> CNotchPass::draw() {
    m_notch->drawPass(g_pHyprRenderer->m_renderData.pMonitor.lock(), m_a);
    return {};
}

bool CNotchPass::needsLiveBlur() {
    return false;
}

bool CNotchPass::needsPrecomputeBlur() {
    return false;
}

const char* CNotchPass::passName() {
    return "CNotchPass";
}

ePassElementType CNotchPass::type() {
    return EK_CUSTOM;
}
