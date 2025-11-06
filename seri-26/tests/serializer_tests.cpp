#include <cassert>
#include <expected>
#include <map>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include <seri/seri.hpp>

using seri::meta::base;
using seri::meta::bases;
using seri::meta::case_;
using seri::meta::cases;
using seri::meta::field;
using seri::meta::fields;

struct Named {
    std::string name;
};

struct Address {
    std::string street;
    int number{};
};

struct Employee : Named {
    int id{};
    Address address;
    std::vector<int> favorite_numbers;
};

enum class Tone { Warm, Cool, Neutral };

namespace seri::meta {
consteval auto reflect(tag<Named>) {
    return describe<Named>(bases(), fields(field<&Named::name>("name")));
}

consteval auto reflect(tag<Address>) {
    return describe<Address>(
        bases(), fields(field<&Address::street>("street"), field<&Address::number>("number")));
}

consteval auto reflect(tag<Employee>) {
    return describe<Employee>(
        bases(base<Named>()),
        fields(field<&Employee::id>("id"), field<&Employee::address>("address"),
               field<&Employee::favorite_numbers>("favorite_numbers")));
}

consteval auto reflect_enum(tag<Tone>) {
    return describe_enum<Tone>(
        cases(case_<Tone, Tone::Warm>("warm"), case_<Tone, Tone::Cool>("cool"),
              case_<Tone, Tone::Neutral>("neutral")));
}
} // namespace seri::meta

static void test_plain_types() {
    seri::json_writer writer;
    seri::serialize(writer, 42);
    assert(writer.str() == "42");

    writer.buffer.clear();
    seri::serialize(writer, 3.5);
    assert(writer.str().starts_with("3.5"));

    writer.buffer.clear();
    seri::serialize(writer, true);
    assert(writer.str() == "true");
}

static void test_strings_and_ranges() {
    auto json = seri::to_json(std::string{"hello"}).str();
    assert(json == "\"hello\"");

    std::vector<int> values{1, 2, 3};
    json = seri::to_json(values).str();
    assert(json == "[1,2,3]");
}

static void test_struct_and_inheritance() {
    Employee alice;
    alice.name = "Alice";
    alice.id = 7;
    alice.address.street = "Fifth";
    alice.address.number = 9;
    alice.favorite_numbers = {3, 5, 7};

    auto json = seri::to_json(alice).str();
    const std::string expected =
        "{\"name\":\"Alice\",\"id\":7,\"address\":{\"street\":\"Fifth\",\"number\":9},"
        "\"favorite_numbers\":[3,5,7]}";
    assert(json == expected);
}

static void test_enums() {
    auto json = seri::to_json(Tone::Cool).str();
    assert(json == "\"cool\"");
}

static void test_maps_optionals_expected() {
    std::map<std::string, int> sample{{"a", 1}, {"b", 2}};
    auto json = seri::to_json(sample).str();
    assert(json == "{\"a\":1,\"b\":2}");

    std::optional<int> opt = 5;
    json = seri::to_json(opt).str();
    assert(json == "5");

    opt.reset();
    json = seri::to_json(opt).str();
    assert(json == "null");

    std::expected<int, std::string> ok = 12;
    json = seri::to_json(ok).str();
    assert(json == "{\"state\":\"value\",\"value\":12}");

    std::expected<int, std::string> err = std::unexpected("boom");
    json = seri::to_json(err).str();
    assert(json == "{\"state\":\"error\",\"error\":\"boom\"}");
}

static void test_variant() {
    std::variant<int, std::string> variant = 3;
    auto json = seri::to_json(variant).str();
    assert(json == "{\"index\":0,\"value\":3}");

    variant = std::string{"hi"};
    json = seri::to_json(variant).str();
    assert(json == "{\"index\":1,\"value\":\"hi\"}");
}

int main() {
    test_plain_types();
    test_strings_and_ranges();
    test_struct_and_inheritance();
    test_enums();
    test_maps_optionals_expected();
    test_variant();
    return 0;
}
