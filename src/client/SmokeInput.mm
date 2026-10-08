#include "client/SmokeInput.h"
#import <Cocoa/Cocoa.h>
#import <Carbon/Carbon.h>

namespace client::smoke {
namespace {
NSWindow* cocoa(void* window) { return (__bridge NSWindow*)window; }
NSPoint location(NSWindow* w, float x, float y) {
    return NSMakePoint(x, w.contentView.frame.size.height - y);
}
NSTimeInterval now() { return [[NSProcessInfo processInfo] systemUptime]; }
void post(NSEvent* event) { [NSApp postEvent:event atStart:NO]; }
}
bool available() { return true; }
void focus(void* window) {
    [NSApp activateIgnoringOtherApps:YES];
    [cocoa(window) makeKeyAndOrderFront:nil];
}
void mouse_move(void* window, float x, float y) {
    NSWindow* w = cocoa(window);
    post([NSEvent mouseEventWithType:NSEventTypeMouseMoved location:location(w, x, y) modifierFlags:0
                           timestamp:now() windowNumber:w.windowNumber context:nil eventNumber:0
                          clickCount:0 pressure:0]);
}
void mouse_button(void* window, bool right, bool down, float x, float y) {
    NSWindow* w = cocoa(window);
    const NSEventType type = right ? (down ? NSEventTypeRightMouseDown : NSEventTypeRightMouseUp)
                                   : (down ? NSEventTypeLeftMouseDown : NSEventTypeLeftMouseUp);
    post([NSEvent mouseEventWithType:type location:location(w, x, y) modifierFlags:0 timestamp:now()
                        windowNumber:w.windowNumber context:nil eventNumber:0 clickCount:1
                            pressure:down ? 1 : 0]);
}
void key(void* window, Key key, bool down) {
    NSWindow* w = cocoa(window);
    unsigned short code = kVK_ANSI_S;
    NSString* text = @"s";
    switch (key) {
    case Key::s: break;
    case Key::left: code = kVK_LeftArrow; text = @""; break;
    case Key::right: code = kVK_RightArrow; text = @""; break;
    case Key::up: code = kVK_UpArrow; text = @""; break;
    case Key::down: code = kVK_DownArrow; text = @""; break;
    case Key::plus: code = kVK_ANSI_Equal; text = @"="; break;
    case Key::minus: code = kVK_ANSI_Minus; text = @"-"; break;
    }
    post([NSEvent keyEventWithType:down ? NSEventTypeKeyDown : NSEventTypeKeyUp location:NSZeroPoint
                     modifierFlags:0 timestamp:now() windowNumber:w.windowNumber context:nil
                        characters:text charactersIgnoringModifiers:text isARepeat:NO keyCode:code]);
}
void scroll(void* window, float lines, float x, float y) {
    NSWindow* w = cocoa(window);
    CGEventRef cg = CGEventCreateScrollWheelEvent(nullptr, kCGScrollEventUnitLine, 1, static_cast<int32_t>(lines));
    const NSPoint inside = [w convertPointToScreen:location(w, x, y)];
    const CGFloat top = NSMaxY([NSScreen screens][0].frame);
    CGEventSetLocation(cg, CGPointMake(inside.x, top - inside.y));
    CGEventSetIntegerValueField(cg, kCGMouseEventWindowUnderMousePointer, w.windowNumber);
    CGEventSetIntegerValueField(cg, kCGMouseEventWindowUnderMousePointerThatCanHandleThisEvent, w.windowNumber);
    post([NSEvent eventWithCGEvent:cg]);
    CFRelease(cg);
}
}
