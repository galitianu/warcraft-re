// Diagnose the historical model's libm boundary. This is not retail evidence.
#include <bit>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numbers>

int main() {
    // Volatile inputs ensure this measures the runtime library, not folding.
    volatile float x = -1.0f, y = 0.0f;
    const float angle = std::atan2(y, x);
    constexpr float degrees_per_radian = 180.0f / std::numbers::pi_v<float>;
    const float heading = angle * degrees_per_radian;
    std::cout << "{\n  \"scope\": \"runtime std::atan2(float(+0), float(-1)); historical v1/v2 heading\",\n"
              << "  \"atan2_bits\": \"" << std::hex << std::bit_cast<std::uint32_t>(angle) << "\",\n"
              << "  \"degrees_per_radian_bits\": \"" << std::bit_cast<std::uint32_t>(degrees_per_radian) << "\",\n"
              << "  \"heading_bits\": \"" << std::bit_cast<std::uint32_t>(heading) << "\",\n"
              << "  \"heading_degrees\": " << std::dec << std::setprecision(9) << heading << "\n}\n";
}
