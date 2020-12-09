/*
 * client.cc
 */
#include <stdio.h>
#include <string.h>
#include <cassert>
#include <algorithm>
#include <iostream>
#include <vector>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <stdlib.h>

#include <kodo_rlnc/coders.hpp>


using namespace std;

int sent_accout=0;

class client
{
	private:
		/* data */
		struct sockaddr_in serv_addr;
	
	public:
		client();
		~client();
		void send_to_Service(vector< vector<uint8_t> > encoded_payloads);
		void send_payload(char IP[], int Port,vector<uint8_t> payload);
		void sent_test(string IP, int Port, string message);
		vector<std::vector<uint8_t>> encode(string IP, int Port);
		
};

client::client()
{

}

client::~client()
{
	cout<< "this client object is deleted" << endl;
}

void client:: send_payload(char IP[], int Port, vector<uint8_t> payload )
{
	vector<uint8_t> *p=&payload;
	int send_num;
	int server_sock = socket(AF_INET, SOCK_DGRAM, 0);

	//set IP & Port in Socket
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));  //set by 0
    serv_addr.sin_family = AF_INET;  //IPv4
    serv_addr.sin_addr.s_addr = inet_addr(IP);  //IP
    serv_addr.sin_port = htons(Port);  //Port

	send_num = sendto(server_sock, &payload, payload.size(), 0, (struct sockaddr *)&serv_addr, sizeof(serv_addr));  
    cout <<("payload is:\n")<< endl;
	
	if(send_num < 0)  
	{  
		perror("sendto error:");  
		exit(1);  
	}  
	else
	{
		++sent_accout;
		cout << "send num is:" << send_num << endl;
	}
}

void sent_test(string IP, int Port, string message)
{
	int send_num;
	int server_sock = socket(AF_INET, SOCK_DGRAM, 0);

	//set IP & Port in Socket
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));  //set by 0
    serv_addr.sin_family = AF_INET;  //IPv4
    serv_addr.sin_addr.s_addr = inet_addr(&(IP[0]));  //IP
    serv_addr.sin_port = htons(Port);  //Port
	char *str= & (message[0]);
	send_num = sendto(server_sock, str, message.length(), 0, (struct sockaddr *)&serv_addr, sizeof(serv_addr));

}

vector< vector<uint8_t> > client:: encode(string IP, int Port)
{
	uint32_t symbols = 42;
	uint32_t symbol_size = 160;
	fifi::finite_field field = fifi::finite_field::binary8;
	kodo_rlnc::encoder encoder(field, symbols, symbol_size);

	// TODO: Generate coded payload and send them through UDP clients.
	// Generate payload
	// Generate block data, use random for test
	vector<uint8_t> block_in(encoder.block_size());
	generate(block_in.begin(), block_in.end(), rand);
	
	encoder.set_symbols_storage(block_in.data());
    
	// set payloads with 2*symbols's vector
	vector< vector<uint8_t> > encoded_payloads(
    symbols * 2, vector<uint8_t>(encoder.max_payload_size()));

	for (auto& payload : encoded_payloads)
    {
        // Encode a packet into the payload buffer
        encoder.produce_payload(payload.data());
		send_payload(&(IP[0]),Port,payload);
    }

	return  encoded_payloads;
}

int main()
{
	client C;
	sent_test("10.0.3.11", 9999,"hello")
	//C.encode("10.0.3.11", 9999);
	//cout<<sent_accout<<endl;
	return 0;
}
