#pragma once

#define WLR_USE_UNSTABLE

#include <string>

#include <hyprland/src/config/values/types/ColorValue.hpp>
#include <hyprland/src/config/values/types/IntValue.hpp>
#include <hyprland/src/config/values/types/StringValue.hpp>
#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/render/OpenGL.hpp>
#include <hyprland/src/render/decorations/IHyprWindowDecoration.hpp>
#include <hyprland/src/render/pass/PassElement.hpp>

inline HANDLE PHANDLE = nullptr;

struct SNotchConfig {
    SP<Config::Values::CColorValue>  active;
    SP<Config::Values::CColorValue>  rule;
    SP<Config::Values::CColorValue>  bg;
    SP<Config::Values::CStringValue> font;
    SP<Config::Values::CIntValue>    fontSize;
};

inline SNotchConfig config;

class CNotch : public IHyprWindowDecoration {
  public:
    explicit CNotch(PHLWINDOW);
    ~CNotch() override;

    SDecorationPositioningInfo getPositioningInfo() override;
    void                       onPositioningReply(const SDecorationPositioningReply& reply) override;
    void                       draw(PHLMONITOR, float const& a) override;
    eDecorationType            getDecorationType() override;
    void                       updateWindow(PHLWINDOW) override;
    void                       damageEntire() override;
    uint64_t                   getDecorationFlags() override;
    eDecorationLayer           getDecorationLayer() override;
    std::string                getDisplayName() override;

    void                       drawPass(PHLMONITOR, float a);

  private:
    CBox                 frameBox();
    bool                 shown();

    PHLWINDOWREF         m_window;
    CBox                 m_assigned;
    SP<Render::ITexture> m_title;
    std::string          m_titleKey;
};

class CNotchPass : public IPassElement {
  public:
    CNotchPass(CNotch* notch, float a);

    std::vector<UP<IPassElement>> draw() override;
    bool                          needsLiveBlur() override;
    bool                          needsPrecomputeBlur() override;
    const char*                   passName() override;
    ePassElementType              type() override;

  private:
    CNotch* m_notch;
    float   m_a;
};
