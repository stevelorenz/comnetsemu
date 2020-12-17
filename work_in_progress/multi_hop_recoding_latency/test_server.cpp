#include <arpa/inet.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <algorithm>
#include <cassert>
#include <iostream>
#include <kodo_rlnc/coders.hpp>
#include <vector>
#include <chrono>
#include <fstream>
#define SERVICE_PORT 9999
int main(int argc, char **argv) {

  struct timeval tv;
  tv.tv_sec = 60;
  tv.tv_usec = 0;
  uint32_t symbols = 42;
  uint32_t symbol_size = 160;
  std::vector<double> decoder_time;
  std::vector<double> values;



  using microsec = std::chrono::duration<double, std::micro>;
  std::chrono::high_resolution_clock::time_point now, start, stop;
  
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
  bool save = true; 
  start = std::chrono::high_resolution_clock::now();
  /* now loop, receiving data and printing what we received */
  while (!decoder.is_complete()) {
    printf("waiting on port %d for packet %d \n", SERVICE_PORT, rec_pkts);
    // Check Socket Timeout
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO,&tv,sizeof(tv)) < 0) {
    }
    recvlen = recvfrom(fd, &(payload[0]), payload.size(), 0,
                       (struct sockaddr *)&remaddr, &addrlen);
    if (recvlen == -1){
    save = false;
    printf("Timeout. Stop receiving. \n");
    break;
    }
    printf("received %d bytes\n", recvlen);

      now = std::chrono::high_resolution_clock::now();
      if (rec_pkts == 0) {
       values.push_back(microsec(now- start).count());
       }
     if (rec_pkts == 1) {
       values.push_back(microsec(now- start).count());
       double time_difference = 10000 * (values[1]-values[0]);
       tv.tv_usec = time_difference;
       tv.tv_sec  = 0;
     }
      now = std::chrono::high_resolution_clock::now();
      decoder.consume_payload(payload.data());
      stop = std::chrono::high_resolution_clock::now();
      double time_difference = microsec(stop -now).count();
      decoder_time.push_back(time_difference);
    
      rec_pkts++;
    }

  
  std::ofstream myfile;
  myfile.open ("decoding_time.csv");
  if (save == true){
  int vsize = decoder_time.size();
    for(int n=0; n<vsize; n++)
     {
     myfile << decoder_time[n] << '\t';
     myfile << "," ;
     }
   }
   else{
   myfile << "failed" ;
  }
  myfile.close();
 

  
  /* never exits */
}
