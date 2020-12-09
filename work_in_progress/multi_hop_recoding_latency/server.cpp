/*
 * server.cc
 */

#include <cassert>
#include <algorithm>
#include <iostream>
#include <vector>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#include <kodo_rlnc/coders.hpp>

using namespace std;


int main()
{
	

	return 0;
}
void test()
{

}
void run()
{
	int sock = socket(AF_INET, SOCK_DGRAM, 0);

	if(sock < 0)  
	{  
    perror("socket");  
    exit(1);  
	}  
	
	// Init Socket
	struct sockaddr_in addr_serv;  
	int len;  
	memset(&addr_serv, 0, sizeof(struct sockaddr_in));  //每个字节都用0填充
	addr_serv.sin_family = AF_INET;  //使用IPV4地址
	addr_serv.sin_port = htons(9999);  
	addr_serv.sin_addr.s_addr =  inet_addr("10.0.3.11");
	len = sizeof(addr_serv); 
	int recv_num; 

	// Bind socket 
	if(bind(sock, (struct sockaddr *)&addr_serv, sizeof(addr_serv)) < 0)  
	{  
		perror("bind error:");  
		exit(1);  
	}  

	// Set up for receive
	struct sockaddr_in client_addr;  
	
	uint32_t symbols = 42;
	uint32_t symbol_size = 160;
	fifi::finite_field field = fifi::finite_field::binary8;

	kodo_rlnc::encoder encoder(field, symbols, symbol_size);
    kodo_rlnc::decoder decoder(field, symbols, symbol_size);

	// Define a data buffer where the symbols should be decoded
    std::vector<uint8_t> block_out(decoder.block_size());
    
	decoder.set_symbols_storage(block_out.data());

	std::vector<std::vector<uint8_t>> encoded_payloads(
        symbols * 2, std::vector<uint8_t>(encoder.max_payload_size()));

	// std::vector<uint8_t> re_payload(encoder.max_payload_size());
	// std::cout <<encoder.max_payload_size();

	while(1)  
	{    
		try
		{
			cout<< "ready to rec, buffer size is:"<<symbols*2*encoder.max_payload_size()<<endl;
			recv_num = recvfrom(sock, &encoded_payloads, symbols*2*encoder.max_payload_size(), 0, (struct sockaddr *)&client_addr, (socklen_t *)sizeof(client_addr));
		}
		catch(const std::exception& e)
		{
			std::cerr <<"recv error"<<e.what() << '\n';
		}
				
		if(recv_num < 0)  
		{  
		perror("recvfrom error:");  
		exit(1);  
		}  

		try
		{
			/* code */
			if (encoded_payloads.size()==2*symbol_size)
			{
				for (auto& payload : encoded_payloads)
				{
					// Pass that packet to the decoder
					decoder.consume_payload(payload.data());
				}

    		}
			if (decoder.is_complete())
				{
					break;
				}
		}
		catch(const std::exception& e)
		{
			std::cerr << "it has a error:" <<e.what() << '\n';
		}
				

		if (decoder.is_complete())
        {
            printf("decoder is complete");
			close(sock); 
			break;
        }
	}
}
