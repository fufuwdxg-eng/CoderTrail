// Runner fixture only. Do not register as an externally curated source.
#include <iostream>
#include <string>
#include <stdexcept>

int main() {
    std::string token;
    long long total = 0;
    int count = 0;
    try {
        while (std::cin >> token) {
            if (++count > 10000) throw std::invalid_argument("count");
            std::size_t start = (token[0] == '+' || token[0] == '-') ? 1 : 0;
            if (start == token.size()) throw std::invalid_argument("empty");
            for (std::size_t i = start; i < token.size(); ++i)
                if (token[i] < '0' || token[i] > '9') throw std::invalid_argument("digit");
            std::size_t end = 0;
            long long value = std::stoll(token, &end);
            if (end != token.size() || value < -1000 || value > 1000)
                throw std::out_of_range("range");
            total += value;
        }
    } catch (const std::exception&) {
        std::cerr << "INVALID\n";
        return 2;
    }
    std::cout << total << '\n';
}
