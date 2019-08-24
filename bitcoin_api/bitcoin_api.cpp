#include <iostream>
#include <string>
#include <string_view>
#include <bitcoin/system.hpp>
#include <pybind11/pybind11.h>

namespace py = pybind11;

bool is_valid_address(std::string address)
{
    return bc::system::wallet::payment_address(address);
}

//const std::string master_chain_code = "xpub68xePK7VvVcVQikShVGveYd8c7eTsU8VW2RmjVpfLuPn2v188qBeT9hhXTsDi3qrTQMj6uuvwMm4jtm6WiySEpSoF54fEaSmqs1mxP3v6W7";

// $ echo e171367ca589c056589c5a837b5f79b3aea61d947b5dccd5 | bx hd-new
const std::string master_chain_code = "tpubD6NzVbkrYhZ4WVyJejvGGNMQ22hjnaJAjJJhb2TPkwWNgek3fY5CLfqF5vysK9XzGz4M7LEVJ4JUuLSVAc36yDhWWsyoVSUrc5rqKg489Mt";

std::string get_address(uint32_t user_id, uint32_t chain_index)
{
	bc::system::wallet::hd_public master(master_chain_code,
		bc::system::wallet::hd_public::testnet);

    BITCOIN_ASSERT(bc::system::wallet::hd_public::testnet == 70617039);
    BITCOIN_ASSERT(master);

	auto user_chain = master.derive_public(user_id);
	auto key_chain = user_chain.derive_public(chain_index);

    BITCOIN_ASSERT(user_chain);
    BITCOIN_ASSERT(key_chain);

	bc::system::wallet::ec_public public_key(key_chain.point());

	auto payaddr = public_key.to_payment_address(0x6f);
    return payaddr.encoded();
}

PYBIND11_MODULE(bitcoin_api, module)
{
    module.def("is_valid_address", &is_valid_address);
    module.def("get_address", &get_address);
}

