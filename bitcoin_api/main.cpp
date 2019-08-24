#include <iostream>
#include <bitcoin/system.hpp>

// $ echo e171367ca589c056589c5a837b5f79b3aea61d947b5dccd5 | bx hd-new -v 70617039
const std::string master_chain_code = "tpubD6NzVbkrYhZ4WVyJejvGGNMQ22hjnaJAjJJhb2TPkwWNgek3fY5CLfqF5vysK9XzGz4M7LEVJ4JUuLSVAc36yDhWWsyoVSUrc5rqKg489Mt";

bc::system::wallet::hd_key decode_key(const std::string& base58)
{
    bc::system::data_chunk value;

    bool decode_success = bc::system::decode_base58(value, base58);
    BITCOIN_ASSERT(decode_success);
    BITCOIN_ASSERT(value.size() == bc::system::wallet::hd_key_size);

    bc::system::wallet::hd_key key;
    std::copy(value.begin(), value.end(), key.begin());
    return key;
}

std::string get_address(uint32_t user_id, uint32_t chain_index)
{
	bc::system::wallet::hd_public master(master_chain_code,
		bc::system::wallet::hd_public::testnet);

    BITCOIN_ASSERT(bc::system::wallet::hd_public::testnet == 70617039);
    BITCOIN_ASSERT(master);

	auto user_chain = master.derive_public(user_id);
    BITCOIN_ASSERT(user_chain);

	auto key_chain = user_chain.derive_public(chain_index);
    BITCOIN_ASSERT(key_chain);

	bc::system::wallet::ec_public public_key(key_chain.point());

	auto payaddr = public_key.to_payment_address(0x6f);
    return payaddr.encoded();
}

int main()
{
    get_address(0, 110);
    return 0;
}

// command.set_secret_version_option(70615956);

