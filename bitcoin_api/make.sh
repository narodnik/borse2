#!/bin/bash
c++ -O3 -Wall -shared -std=c++17 -fPIC `python3 -m pybind11 --includes` bitcoin_api.cpp -o bitcoin_api`python3-config --extension-suffix` $(pkg-config --cflags --libs libbitcoin-system)
