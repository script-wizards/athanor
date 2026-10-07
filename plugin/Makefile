CXXFLAGS ?= -O2
CXXFLAGS += -shared -fPIC -std=c++2b -Wall
ifeq ($(CXX),g++)
    CXXFLAGS += --no-gnu-unique
endif
INCLUDES = `pkg-config --cflags pixman-1 libdrm hyprland pangocairo libinput libudev wayland-server xkbcommon`
OUT ?= athanor-notch.so

$(OUT): main.cpp notch.cpp notch.hpp
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(INCLUDES) main.cpp notch.cpp -o $@

clean:
	rm -f $(OUT)

.PHONY: clean
