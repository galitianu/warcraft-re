#pragma once
// Smoke-test input (docs/client-v1.md): posts native window-system events into this
// application's own event queue, so they reach raylib through the same Cocoa ->
// GLFW -> raylib path as a physical mouse and keyboard. macOS only; it needs no
// accessibility permission because it never posts to another application.
// Coordinates are window points from the top-left, as raylib reports the mouse.
namespace client::smoke {
enum class Key { s, left, right, up, down, plus, minus };
bool available();
void focus(void* window);
void mouse_move(void* window, float x, float y);
void mouse_button(void* window, bool right, bool down, float x, float y);
void key(void* window, Key key, bool down);
void scroll(void* window, float lines, float x, float y);
}
