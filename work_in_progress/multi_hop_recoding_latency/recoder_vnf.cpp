/*
 * recoder_vnf.cc
 */

#include <signal.h>
#include <unistd.h>

#include <cassert>
#include <cstdint>
#include <iostream>

#include <rte_cycles.h>
#include <rte_eal.h>
#include <rte_ethdev.h>
#include <rte_ether.h>
#include <rte_ip.h>
#include <rte_memcpy.h>
#include <rte_udp.h>

#include <ffpp/config.h>
#include <ffpp/munf.h>

#include <kodo_rlnc/coders.hpp>

#include <gsl/gsl>

using namespace gsl;

static constexpr uint16_t BURST_SIZE = 64;
static constexpr int MAX_APU_SIZE = 64 * 1024; // Bytes

static volatile bool force_quit = false;
static struct rte_ether_addr tx_port_addr;

static void signal_handler(int signum)
{
	if (signum == SIGINT || signum == SIGTERM) {
		force_quit = true;
	}
}

void run_store_forward_loop(const struct ffpp_munf_manager &manager)
{
	struct rte_mbuf *rx_buffer[BURST_SIZE];
	uint16_t r = 0;
	struct rte_mbuf *tx_buffer[BURST_SIZE];
	uint16_t t = 0;
	struct rte_mbuf *m;

	uint16_t nb_rx = 0;
	struct rte_ether_hdr *eth_hdr;
	struct rte_ipv4_hdr *ipv4_hdr;
	struct rte_udp_hdr *udp_hdr;

	std::cout << "[MEICA_DIST] Enter store and forward loop." << std::endl;
	while (!force_quit) {
		nb_rx = rte_eth_rx_burst(manager.rx_port_id, 0, rx_buffer,
					 BURST_SIZE);
		if (nb_rx == 0) {
			rte_delay_us_block(1e3);
			continue;
		}
		t = 0;
		for (r = 0; r < nb_rx; ++r) {
			m = rx_buffer[r];
			eth_hdr = rte_pktmbuf_mtod(m, struct rte_ether_hdr *);
			if (eth_hdr->ether_type !=
			    rte_cpu_to_be_16(RTE_ETHER_TYPE_IPV4)) {
				// Avoid mem-leaks.
				rte_pktmbuf_free(m);
				continue;
			}
			ipv4_hdr = rte_pktmbuf_mtod_offset(
				m, struct rte_ipv4_hdr *,
				sizeof(struct rte_ether_hdr));
			if (ipv4_hdr->next_proto_id != IPPROTO_UDP) {
				rte_pktmbuf_free(m);
				continue;
			}

			std::cout << "Recv a UDP packet." << std::endl;
			// Assume there is no IP options.
			udp_hdr = (struct rte_udp_hdr
					   *)((unsigned char *)ipv4_hdr +
					      sizeof(struct rte_ipv4_hdr));
			// Disable UDP checksum
			udp_hdr->dgram_cksum = rte_cpu_to_be_16(0);

			tx_buffer[t] = rx_buffer[r];
			++t;
		}

		rte_eth_tx_burst(manager.tx_port_id, 0, tx_buffer, nb_rx);
	}
}

void run_compute_forward_loop(const struct ffpp_munf_manager &manager)
{
	// TODO: Recode received UDP packets.
	// Remeber to update IP checksums.
	// DPDK API: https://doc.dpdk.org/api-19.11/
	struct rte_mbuf *rx_buffer[BURST_SIZE];
	uint16_t r = 0;
	struct rte_mbuf *tx_buffer[BURST_SIZE];
	uint16_t t = 0;
	struct rte_mbuf *m;

	uint16_t nb_rx = 0;
	struct rte_ether_hdr *eth_hdr;
	struct rte_ipv4_hdr *ipv4_hdr;
	struct rte_udp_hdr *udp_hdr;

	std::cout << "[MEICA_DIST] Enter store and forward loop." << std::endl;
	while (!force_quit) {
		nb_rx = rte_eth_rx_burst(manager.rx_port_id, 0, rx_buffer,
					 BURST_SIZE);
		if (nb_rx == 0) {
			rte_delay_us_block(1e3);
			continue;
		}
		t = 0;
		for (r = 0; r < nb_rx; ++r) {
			m = rx_buffer[r];
			eth_hdr = rte_pktmbuf_mtod(m, struct rte_ether_hdr *);
			if (eth_hdr->ether_type !=
			    rte_cpu_to_be_16(RTE_ETHER_TYPE_IPV4)) {
				// Avoid mem-leaks.
				rte_pktmbuf_free(m);
				continue;
			}
			ipv4_hdr = rte_pktmbuf_mtod_offset(
				m, struct rte_ipv4_hdr *,
				sizeof(struct rte_ether_hdr));
			if (ipv4_hdr->next_proto_id != IPPROTO_UDP) {
				rte_pktmbuf_free(m);
				continue;
			}

			std::cout << "Recv a UDP packet." << std::endl;
			// Assume there is no IP options.
			udp_hdr = (struct rte_udp_hdr
					   *)((unsigned char *)ipv4_hdr +
					      sizeof(struct rte_ipv4_hdr));
			// Disable UDP checksum
			udp_hdr->dgram_cksum = rte_cpu_to_be_16(0);

			tx_buffer[t] = rx_buffer[r];
			++t;
		}

		rte_eth_tx_burst(manager.tx_port_id, 0, tx_buffer, nb_rx);
	}
}

int main(int argc, char *argv[])
{
	int ret;
	ret = rte_eal_init(argc, argv);
	if (ret < 0) {
		rte_exit(EXIT_FAILURE, "Invalid EAL arguments.\n");
	}
	argc -= ret;
	argv += ret;
	force_quit = false;
	signal(SIGINT, signal_handler);
	signal(SIGTERM, signal_handler);

	int opt = 0;
	opterr = 0;
	std::string mode = "store_forward";

	// Retrieve the options:
	while ((opt = getopt(argc, argv, "m:")) != -1) {
		switch (opt) {
		case 'm':
			mode = std::string(optarg);
			break;
		case '?': // unknown option...
			std::cerr << "Error: Unknown option: '" << char(optopt)
				  << "'!" << std::endl;
			break;
		}
	}

	if (mode == "store_forward" || mode == "compute_forward") {
		std::cout << "- Current mode: " << mode << std::endl;
	} else {
		std::cerr << "Error: Unknown mode: " << mode << std::endl;
		rte_eal_cleanup();
		return 0;
	}

	// TODO (Zuo): Use the wrapper class.
	struct ffpp_munf_manager munf_manager;
	struct rte_mempool *pool = NULL;
	ffpp_munf_init_manager(&munf_manager, "test_manager", pool);
	ret = rte_eth_macaddr_get(munf_manager.tx_port_id, &tx_port_addr);
	if (ret < 0) {
		rte_exit(EXIT_FAILURE, "Cannot get the MAC address.\n");
	}

	if (mode == "store_forward") {
		run_store_forward_loop(munf_manager);
	} else if (mode == "compute_forward") {
		run_compute_forward_loop(munf_manager);
	}

	std::cout << "Main loop ends, run cleanups..." << std::endl;
	ffpp_munf_cleanup_manager(&munf_manager);
	rte_eal_cleanup();

	return 0;
}
