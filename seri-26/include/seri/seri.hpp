#pragma once

#include <array>
#include <charconv>
#include <concepts>
#include <cstddef>
#include <expected>
#include <map>
#include <optional>
#include <ranges>
#include <source_location>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

#if defined(SERI_USE_STD_REFLECTION) && __has_include(<experimental/reflect>)
#    include <experimental/reflect>
#    define SERI_DETAIL_HAS_STD_REFLECTION 1
#else
#    define SERI_DETAIL_HAS_STD_REFLECTION 0
#endif

namespace seri {

struct serialization_error {
    std::string message;
    std::source_location where = std::source_location::current();
};

struct json_writer {
    std::string buffer;

    void write(char c) { buffer.push_back(c); }

    void write(std::string_view view) { buffer.append(view); }

    void write_escaped(std::string_view view) {
        write('"');
        for (char c : view) {
            switch (c) {
            case '\\':
                buffer.append("\\\\");
                break;
            case '\"':
                buffer.append("\\\"");
                break;
            case '\n':
                buffer.append("\\n");
                break;
            case '\r':
                buffer.append("\\r");
                break;
            case '\t':
                buffer.append("\\t");
                break;
            default:
                buffer.push_back(c);
                break;
            }
        }
        write('"');
    }

    [[nodiscard]] std::string str() const { return buffer; }
};

namespace meta {

template <typename T>
struct tag {};

template <auto Ptr>
struct member_pointer_traits;

template <typename Class, typename Member, Member Class::*Ptr>
struct member_pointer_traits<Ptr> {
    using class_type = Class;
    using value_type = Member;
};

template <auto Ptr>
struct field_descriptor {
    using traits = member_pointer_traits<Ptr>;
    using class_type = typename traits::class_type;
    using value_type = typename traits::value_type;

    std::string_view name;

    constexpr explicit field_descriptor(std::string_view n) : name(n) {}

    constexpr value_type &get(class_type &object) const noexcept { return object.*Ptr; }
    constexpr const value_type &get(const class_type &object) const noexcept { return object.*Ptr; }
};

template <auto Ptr>
[[nodiscard]] constexpr auto field(std::string_view name) {
    return field_descriptor<Ptr>{name};
}

template <typename Base>
struct base_descriptor {
    using type = Base;
};

template <typename Base>
[[nodiscard]] constexpr auto base() {
    return base_descriptor<Base>{};
}

template <typename T, typename BasesTuple, typename FieldsTuple>
struct type_descriptor {
    BasesTuple bases;
    FieldsTuple fields;
};

template <typename... Bases>
[[nodiscard]] constexpr auto bases(Bases... values) {
    return std::tuple{values...};
}

template <typename... Fields>
[[nodiscard]] constexpr auto fields(Fields... values) {
    return std::tuple{values...};
}

template <typename T, typename BasesTuple, typename FieldsTuple>
[[nodiscard]] constexpr auto describe(BasesTuple bases, FieldsTuple fields) {
    return type_descriptor<T, BasesTuple, FieldsTuple>{bases, fields};
}

template <typename Enum, Enum Value>
struct enum_case_descriptor {
    std::string_view name;
    static constexpr Enum value = Value;

    constexpr explicit enum_case_descriptor(std::string_view n) : name(n) {}
};

template <typename Enum, Enum Value>
[[nodiscard]] constexpr auto case_(std::string_view name) {
    return enum_case_descriptor<Enum, Value>{name};
}

template <typename... Cases>
[[nodiscard]] constexpr auto cases(Cases... descriptors) {
    return std::tuple{descriptors...};
}

template <typename Enum, typename CasesTuple>
struct enum_descriptor {
    CasesTuple cases;

    [[nodiscard]] constexpr std::optional<std::string_view> name_of(Enum value) const noexcept {
        std::optional<std::string_view> result;
        std::apply(
            [&](auto... descriptors) {
                auto assign = [&](const auto &descriptor) {
                    if (!result && descriptor.value == value) {
                        result = descriptor.name;
                    }
                };
                (assign(descriptors), ...);
            },
            cases);
        return result;
    }

    [[nodiscard]] constexpr std::optional<Enum> value_of(std::string_view name) const noexcept {
        std::optional<Enum> result;
        std::apply(
            [&](auto... descriptors) {
                auto assign = [&](const auto &descriptor) {
                    if (!result && descriptor.name == name) {
                        result = descriptor.value;
                    }
                };
                (assign(descriptors), ...);
            },
            cases);
        return result;
    }
};

template <typename Enum, typename CasesTuple>
[[nodiscard]] constexpr auto describe_enum(CasesTuple cases) {
    return enum_descriptor<Enum, CasesTuple>{cases};
}

template <typename Enum>
[[nodiscard]] constexpr auto empty_enum() {
    return enum_descriptor<Enum, std::tuple<>>{std::tuple{}};
}

template <typename T>
concept has_custom_reflect = requires { reflect(tag<T>{}); };

template <typename Enum>
concept has_custom_enum_reflect = requires { reflect_enum(tag<Enum>{}); };

namespace detail {

#if SERI_DETAIL_HAS_STD_REFLECTION
namespace stdr = std::experimental::reflect;

template <typename T>
concept std_meta_struct = requires {
    { stdr::get_data_members(reflexpr(T)) };
};

template <typename Enum>
concept std_meta_enum = requires {
    { stdr::get_enumerators(reflexpr(Enum)) };
};

template <typename T>
consteval auto reflect_with_std_meta() {
    constexpr auto type_info = reflexpr(T);
    constexpr auto base_infos = stdr::get_base_classes(type_info);
    constexpr auto member_infos = stdr::get_data_members(type_info);

    auto make_bases = [&] {
        if constexpr (stdr::is_empty(base_infos)) {
            return bases();
        } else {
            return std::apply(
                [&](auto... base_info) {
                    return bases(base<typename stdr::get_reflected_type<decltype(base_info)>::type>()...);
                },
                base_infos);
        }
    };

    auto make_fields = [&] {
        if constexpr (stdr::is_empty(member_infos)) {
            return fields();
        } else {
            return std::apply(
                [&](auto... member_info) {
                    return fields(field<stdr::get_pointer_v<decltype(member_info)>>(
                        stdr::get_name_v<decltype(member_info)>)...);
                },
                member_infos);
        }
    };

    return describe<T>(make_bases(), make_fields());
}

template <typename Enum>
consteval auto reflect_enum_with_std_meta() {
    constexpr auto enum_info = reflexpr(Enum);
    constexpr auto enumerators = stdr::get_enumerators(enum_info);

    if constexpr (stdr::is_empty(enumerators)) {
        return empty_enum<Enum>();
    } else {
        return std::apply(
            [](auto... enumerator_info) {
                return describe_enum<Enum>(
                    cases(case_<Enum, stdr::get_constant_v<decltype(enumerator_info)>>(
                        stdr::get_name_v<decltype(enumerator_info)>)...));
            },
            enumerators);
    }
}
#endif

template <typename T>
inline constexpr bool can_std_reflect =
#if SERI_DETAIL_HAS_STD_REFLECTION
    std_meta_struct<T>;
#else
    false;
#endif

template <typename Enum>
inline constexpr bool can_std_reflect_enum =
#if SERI_DETAIL_HAS_STD_REFLECTION
    std_meta_enum<Enum>;
#else
    false;
#endif

} // namespace detail

template <typename T>
inline constexpr bool has_type_description_v =
    detail::can_std_reflect<T> || has_custom_reflect<T>;

template <typename Enum>
inline constexpr bool has_enum_description_v =
    detail::can_std_reflect_enum<Enum> || has_custom_enum_reflect<Enum>;

template <typename T>
[[nodiscard]] consteval auto type_description() {
    if constexpr (detail::can_std_reflect<T>) {
#if SERI_DETAIL_HAS_STD_REFLECTION
        return detail::reflect_with_std_meta<T>();
#else
        static_assert(!sizeof(T), "Standard reflection requested but not available");
#endif
    } else if constexpr (has_custom_reflect<T>) {
        return reflect(tag<T>{});
    } else {
        static_assert(!sizeof(T), "Type requires reflection metadata");
    }
}

template <typename Enum>
[[nodiscard]] consteval auto enum_description() {
    if constexpr (detail::can_std_reflect_enum<Enum>) {
#if SERI_DETAIL_HAS_STD_REFLECTION
        return detail::reflect_enum_with_std_meta<Enum>();
#else
        return empty_enum<Enum>();
#endif
    } else if constexpr (has_custom_enum_reflect<Enum>) {
        return reflect_enum(tag<Enum>{});
    } else {
        return empty_enum<Enum>();
    }
}

} // namespace meta

namespace detail {

template <typename T>
concept reflectable = meta::has_type_description_v<T>;

template <typename Enum>
concept enum_reflectable = requires { meta::enum_description<Enum>(); };

template <typename T>
concept string_like = requires(T value) {
    std::string_view(value);
} && !std::is_same_v<std::remove_cvref_t<T>, char>;

template <typename T>
concept map_like = std::ranges::range<T> && requires(T value) {
    typename std::remove_cvref_t<std::ranges::range_value_t<T>>::first_type;
    typename std::remove_cvref_t<std::ranges::range_value_t<T>>::second_type;
};

template <typename T>
concept range_like = std::ranges::range<T> && !string_like<T>;

template <typename T>
struct optional_traits : std::false_type {};

template <typename U>
struct optional_traits<std::optional<U>> : std::true_type {
    using value_type = U;
};

template <typename T>
concept optional_like = optional_traits<std::remove_cvref_t<T>>::value;

template <typename T>
struct expected_traits : std::false_type {};

template <typename Value, typename Error>
struct expected_traits<std::expected<Value, Error>> : std::true_type {
    using value_type = Value;
    using error_type = Error;
};

template <typename T>
concept expected_like = expected_traits<std::remove_cvref_t<T>>::value;

template <typename T>
struct variant_traits : std::false_type {};

template <typename... Ts>
struct variant_traits<std::variant<Ts...>> : std::true_type {};

template <typename T>
concept variant_like = variant_traits<std::remove_cvref_t<T>>::value;

} // namespace detail

template <typename T>
void serialize(json_writer &out, const T &value);

namespace detail {

inline void write_delimiter(json_writer &out, bool &first) {
    if (first) {
        first = false;
    } else {
        out.write(',');
    }
}

inline void serialize_boolean(json_writer &out, bool value) {
    out.write(value ? "true" : "false");
}

template <std::integral T>
void serialize_integral(json_writer &out, T value) {
    char buffer[64];
    auto [ptr, ec] = std::to_chars(std::begin(buffer), std::end(buffer), value);
    if (ec != std::errc{}) {
        throw serialization_error{.message = "integral conversion failed"};
    }
    out.write(std::string_view(buffer, static_cast<std::size_t>(ptr - buffer)));
}

template <std::floating_point T>
void serialize_floating(json_writer &out, T value) {
    char buffer[128];
    auto [ptr, ec] = std::to_chars(std::begin(buffer), std::end(buffer), value);
    if (ec != std::errc{}) {
        throw serialization_error{.message = "floating conversion failed"};
    }
    out.write(std::string_view(buffer, static_cast<std::size_t>(ptr - buffer)));
}

template <typename T>
void serialize_string(json_writer &out, const T &value) {
    out.write_escaped(std::string_view(value));
}

template <typename T>
void serialize_sequence(json_writer &out, const T &range) {
    out.write('[');
    bool first = true;
    for (auto &&element : range) {
        write_delimiter(out, first);
        serialize(out, element);
    }
    out.write(']');
}

template <typename T>
void serialize_map(json_writer &out, const T &range) {
    out.write('{');
    bool first = true;
    for (auto &&pair : range) {
        using key_type = std::remove_cvref_t<decltype(pair.first)>;
        static_assert(string_like<key_type>, "JSON map keys must be string-like");
        write_delimiter(out, first);
        serialize_string(out, pair.first);
        out.write(':');
        serialize(out, pair.second);
    }
    out.write('}');
}

template <typename T, typename Descriptor, typename Fn>
void for_each_field(const T &object, const Descriptor &descriptor, Fn &&fn);

template <typename T, typename Descriptor, typename Fn>
void for_each_field_impl(const T &object, const Descriptor &descriptor, Fn &&fn) {
    std::apply(
        [&](auto... bases) {
            (for_each_field(static_cast<const typename decltype(bases)::type &>(object),
                            meta::type_description<typename decltype(bases)::type>(), fn), ...);
        },
        descriptor.bases);

    std::apply(
        [&](auto... fields) {
            (fn(fields.name, fields.get(object)), ...);
        },
        descriptor.fields);
}

template <typename T, typename Descriptor, typename Fn>
void for_each_field(const T &object, const Descriptor &descriptor, Fn &&fn) {
    for_each_field_impl(object, descriptor, std::forward<Fn>(fn));
}

inline void serialize_object_begin(json_writer &out) { out.write('{'); }
inline void serialize_object_end(json_writer &out) { out.write('}'); }

template <typename T>
void serialize_object(json_writer &out, const T &value) {
    auto descriptor = meta::type_description<std::remove_cvref_t<T>>();
    serialize_object_begin(out);
    bool first = true;
    for_each_field(value, descriptor, [&](std::string_view name, const auto &field) {
        write_delimiter(out, first);
        out.write_escaped(name);
        out.write(':');
        serialize(out, field);
    });
    serialize_object_end(out);
}

template <typename Enum>
void serialize_enum(json_writer &out, Enum value) {
    auto descriptor = meta::enum_description<Enum>();
    if (auto name = descriptor.name_of(value)) {
        out.write_escaped(*name);
    } else {
        serialize_integral(out, static_cast<std::underlying_type_t<Enum>>(value));
    }
}

} // namespace detail

template <typename T>
void serialize(json_writer &out, const T &value) {
    using U = std::remove_cvref_t<T>;
    if constexpr (std::same_as<U, bool>) {
        detail::serialize_boolean(out, value);
    } else if constexpr (std::is_integral_v<U> && !std::same_as<U, bool>) {
        detail::serialize_integral(out, value);
    } else if constexpr (std::is_floating_point_v<U>) {
        detail::serialize_floating(out, value);
    } else if constexpr (detail::string_like<U>) {
        detail::serialize_string(out, value);
    } else if constexpr (std::is_enum_v<U>) {
        detail::serialize_enum(out, value);
    } else if constexpr (detail::map_like<U>) {
        detail::serialize_map(out, value);
    } else if constexpr (detail::range_like<U>) {
        detail::serialize_sequence(out, value);
    } else if constexpr (detail::optional_like<U>) {
        if (value.has_value()) {
            serialize(out, *value);
        } else {
            out.write("null");
        }
    } else if constexpr (detail::expected_like<U>) {
        out.write('{');
        auto idx_field = [&] {
            out.write_escaped("state");
            out.write(':');
        };
        if (value.has_value()) {
            idx_field();
            detail::serialize_string(out, std::string_view{"value"});
            out.write(',');
            out.write_escaped("value");
            out.write(':');
            serialize(out, value.value());
        } else {
            idx_field();
            detail::serialize_string(out, std::string_view{"error"});
            out.write(',');
            out.write_escaped("error");
            out.write(':');
            serialize(out, value.error());
        }
        out.write('}');
    } else if constexpr (detail::variant_like<U>) {
        auto index = value.index();
        std::visit(
            [&](const auto &alt) {
                detail::serialize_object_begin(out);
                bool first = true;
                detail::write_delimiter(out, first);
                out.write_escaped("index");
                out.write(':');
                detail::serialize_integral(out, static_cast<std::size_t>(index));
                detail::write_delimiter(out, first);
                out.write_escaped("value");
                out.write(':');
                serialize(out, alt);
                detail::serialize_object_end(out);
            },
            value);
    } else if constexpr (detail::reflectable<U>) {
        detail::serialize_object(out, value);
    } else {
        static_assert(!sizeof(T), "Type is not serializable");
    }
}

inline json_writer to_json(const auto &value) {
    json_writer writer;
    serialize(writer, value);
    return writer;
}

#define SERI_STRUCT(TYPE, BASES, FIELDS)                                                         \
    friend consteval auto describe(::seri::meta::tag<TYPE>) {                                    \
        using namespace ::seri::meta;                                                            \
        return describe<TYPE>(BASES, FIELDS);                                                     \
    }

#define SERI_ENUM(TYPE, CASES)                                                                   \
    consteval auto describe_enum(::seri::meta::tag<TYPE>) {                                      \
        using namespace ::seri::meta;                                                            \
        return describe_enum<TYPE>(CASES);                                                       \
    }

} // namespace seri
