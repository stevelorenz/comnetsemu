/*
 * client.cc
 */

#include <cassert>
#include <algorithm>
#include <iostream>
#include <vector>

#include <kodo_rlnc/coders.hpp>

int main()
{
	uint32_t symbols = 42;
	uint32_t symbol_size = 160;
	fifi::finite_field field = fifi::finite_field::binary8;
	kodo_rlnc::encoder encoder(field, symbols, symbol_size);

	// TODO: Generate coded payload and send them through UDP clients.

	return 0;
}
