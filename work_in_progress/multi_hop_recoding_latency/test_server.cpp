#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <algorithm>
#include <cassert>
#include <iostream>
#include <kodo_rlnc/coders.hpp>
#include <vector>
#include <chrono>
#include <fstream>
#define SERVICE_PORT 9999
int main(int argc, char **argv) {
  uint32_t symbols = 42;
  uint32_t symbol_size = 160;
  std::vector<double> decoder_time;

  using microsec = std::chrono::duration<double, std::micro>;
  std::chrono::high_resolution_clock::time_point start, stop;
  
  fifi::finite_field field = fifi::finite_field::binary8;
  kodo_rlnc::decoder decoder(field, symbols, symbol_size);

  // Allocate some storage for a "payload" the payload is what we would
  // eventually send over a network
  std::vector<uint8_t> payload(decoder.max_payload_size());

  // Define data buffers where the symbols should be decoded
  std::vector<uint8_t> data_out(decoder.block_size());

  decoder.set_symbols_storage(data_out.data());

  struct sockaddr_in myaddr;           /* our address */
  struct sockaddr_in remaddr;          /* remote address */
  socklen_t addrlen = sizeof(remaddr); /* length of addresses */
  int recvlen;                         /* # bytes received */
  int fd;                              /* our socket */

  /* create a UDP socket */

  if ((fd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("cannot create socket\n");
    return 0;
  }

  /* bind the socket to any valid IP address and a specific port */

  memset((char *)&myaddr, 0, sizeof(myaddr));
  myaddr.sin_family = AF_INET;
  myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
  myaddr.sin_port = htons(SERVICE_PORT);

  if (bind(fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) < 0) {
    perror("bind failed");
    return 0;
  }

  int rec_pkts = 0;
  /* now loop, receiving data and printing what we received */
  while (rec_pkts < 42) {
    printf("waiting on port %d for packet %d \n", SERVICE_PORT, rec_pkts);
    recvlen = recvfrom(fd, &(payload[0]), payload.size(), 0,
                       (struct sockaddr *)&remaddr, &addrlen);
    printf("received %d bytes\n", recvlen);

      start = std::chrono::high_resolution_clock::now();
      decoder.consume_payload(payload.data());
      stop = std::chrono::high_resolution_clock::now();
      double time_difference = microsec(stop -start).count();
      decoder_time.push_back(time_difference);
      rec_pkts++;
    }
  

  
  std::ofstream myfile;
  myfile.open ("decoding_time.csv");
  int vsize = decoder_time.size();
    for(int n=0; n<vsize; n++)
     {
     myfile << decoder_time[n] << '\t';
     myfile << "," ;
     }
  myfile.close(); 

  
  /* never exits */
}
