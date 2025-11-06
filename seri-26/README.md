# seri-26

`seri-26` is a research prototype for a terse serialization library experimenting with C++26
metaprogramming idioms. The library focuses on providing zero-boilerplate JSON emission for
plain types, structured aggregates, enums, modern standard containers, `std::optional`,
`std::expected`, and `std::variant`.

## Highlights

- Header-only interface that leans on `consteval` descriptors and concepts to reduce the
  chance of misconfiguration.
- Macro-free registration of struct and enum metadata via `consteval` overloads that pair
  naturally with reflection facilities.
- Optional integration hook for the upcoming C++26 static reflection: define
  `SERI_USE_STD_REFLECTION` and include `<experimental/reflect>` to let the library harvest
  fields and bases automatically.
- Recursive flattening of bases allows serializing class hierarchies without custom code.
- `json_writer` offers a minimal surface for producing JSON text while preserving performance.

## Building

The project uses CMake with Ninja:

```bash
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build
```

The CMake configuration requests C++26, and appends `-std=c++2b` for contemporary GCC/Clang
setups that implement the upcoming standard.

## Usage snippet

```cpp
#include <seri/seri.hpp>

struct Vec3 {
    float x{};
    float y{};
    float z{};
};

namespace seri::meta {
consteval auto reflect(tag<Vec3>) {
    return describe<Vec3>(
        bases(), fields(field<&Vec3::x>("x"), field<&Vec3::y>("y"), field<&Vec3::z>("z")));
}
} // namespace seri::meta

int main() {
    Vec3 v{1.0f, 2.0f, 3.0f};
    auto json = seri::to_json(v).str();
    // json == "{\"x\":1,\"y\":2,\"z\":3}"
}
```

When C++26 static reflection becomes widely available, the explicit `reflect` overloads can be
replaced by the automatically generated metadata path by compiling with
`-DSERI_USE_STD_REFLECTION` and including the proposed `<experimental/reflect>` header.
