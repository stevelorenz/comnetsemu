#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <algorithm>
#include <cassert>
#include <iostream>
#include <kodo_rlnc/coders.hpp>
#include <vector>
#include <chrono>
#define SERVICE_PORT 9999

int main(void) {
  uint32_t data_rate = 1000;
  uint32_t interleaving_batch;
  uint32_t current_batch = 0;
  uint32_t symbols = 42;
  uint32_t symbol_size = 160;
  fifi::finite_field field = fifi::finite_field::binary8;
  kodo_rlnc::encoder encoder(field, symbols, symbol_size);

  using microsec = std::chrono::duration<double, std::micro>;
  std::chrono::high_resolution_clock::time_point start, stop, now;

  // Allocate some storage for a "payload" the payload is what we would
  // eventually send over a network
  std::vector<uint8_t> payload(encoder.max_payload_size());

  // Allocate some data to encode. In this case we make a buffer
  // with the same size as the encoder's block size (the max.
  // amount a single encoder can encode)
  std::vector<uint8_t> data_in(encoder.block_size());

  // Just for fun - fill the data with random data
  std::generate(data_in.begin(), data_in.end(), rand);
  
  // Assign the data buffer to the encoder so that we may start
  // to produce encoded symbols from it
  encoder.set_symbols_storage(data_in.data());


  struct sockaddr_in myaddr, remaddr;
  int fd, i, slen = sizeof(remaddr);
  const char *server = "10.0.3.11";

  /* create a socket */

  if ((fd = socket(AF_INET, SOCK_DGRAM, 0)) == -1) printf("socket created\n");

  /* bind it to all local addresses and pick any port number */

  memset((char *)&myaddr, 0, sizeof(myaddr));
  myaddr.sin_family = AF_INET;
  myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
  myaddr.sin_port = htons(0);

  if (bind(fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
    perror("bind failed");
    return 0;
  }

  /* now define remaddr, the address to whom we want to send messages */
  /* For convenience, the host address is expressed as a numeric IP address */
  /* that we will convert to a binary format via inet_aton */

  memset((char *)&remaddr, 0, sizeof(remaddr));
  remaddr.sin_family = AF_INET;
  remaddr.sin_port = htons(SERVICE_PORT);
  if (inet_aton(server, &remaddr.sin_addr) == 0) {
    fprintf(stderr, "inet_aton() failed\n");
    exit(1);
  }

  // now let's send the messages
  uint32_t packets_sent = 0;
  start = std::chrono::high_resolution_clock::now();
  while (packets_sent < encoder.rank()) {

            // Stall the sending thread to match the desired data rate
            while (true)
            {
                now = std::chrono::high_resolution_clock::now();
                double elapsed_time = microsec(now - start).count();
                double current_rate = packets_sent / elapsed_time;

                // Exit the while loop if the current rate drops below the
                // desired rate
                if (current_rate * 1000000 <= data_rate)
                    break;
            }

    encoder.produce_payload(payload.data());

    printf("Sending packet %d to %s port %d\n", packets_sent, server, SERVICE_PORT);
    if (sendto(fd, &(payload[0]), payload.size(), 0,
               (struct sockaddr *)&remaddr, slen) == -1)
      perror("sendto");
    packets_sent++;
  }
  close(fd);
  return 0;
}
