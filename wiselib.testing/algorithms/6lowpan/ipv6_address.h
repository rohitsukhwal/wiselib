/***************************************************************************
 ** This file is part of the generic algorithm library Wiselib.           **
 ** Copyright (C) 2008,2009 by the Wisebed (www.wisebed.eu) project.      **
 **                                                                       **
 ** The Wiselib is free software: you can redistribute it and/or modify   **
 ** it under the terms of the GNU Lesser General Public License as        **
 ** published by the Free Software Foundation, either version 3 of the    **
 ** License, or (at your option) any later version.                       **
 **                                                                       **
 ** The Wiselib is distributed in the hope that it will be useful,        **
 ** but WITHOUT ANY WARRANTY; without even the implied warranty of        **
 ** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         **
 ** GNU Lesser General Public License for more details.                   **
 **                                                                       **
 ** You should have received a copy of the GNU Lesser General Public      **
 ** License along with the Wiselib.                                       **
 ** If not, see <http://www.gnu.org/licenses/>.                           **
 ***************************************************************************/
#ifndef __ALGORITHMS_6LOWPAN_IPV6_ADDR_H__
#define __ALGORITHMS_6LOWPAN_IPV6_ADDR_H__


namespace wiselib
{
	template<typename Radio_P, typename Debug_P>
	class IPv6Address
	{
	public:
	
	typedef Debug_P Debug;
	typedef Radio_P Radio;
	typedef typename Radio::node_id_t link_layer_node_id_t;
	
	IPv6Address()
	{
		memset(addr,0, 16);
		prefix_length = 0;
	}
	
	//----------------------------------------------------------------------------
	IPv6Address(const IPv6Address& address)
	{
		memcpy(addr, address.addr, 16);
		prefix_length = address.prefix_length;
	}
	
	//----------------------------------------------------------------------------
	IPv6Address(const uint8_t* addr)
	{
		memcpy(addr, addr, 16);
		prefix_length = 64;
	}
	
	//----------------------------------------------------------------------------
	//Constructor for static pre defined addresses
	IPv6Address(int type)
	{
		//"Broadcast" (Multicast) - FF02:0:0:0:0:0:0:1
		if ( type == 1 )
		{
			addr[0]=0xFF;
			addr[1]=0x02;
			memset(addr+2,0,13);
			addr[15]=0x01;
			prefix_length = 64;
		}
		//All routers' address - FF02:0:0:0:0:0:0:2
		else if( type == 2 )
		{
			addr[0]=0xFF;
			addr[1]=0x02;
			memset(addr+2,0,13);
			addr[15]=0x02;
			prefix_length = 64;
		}
		//Unspecified address - NULL NODE ID - 0:0:0:0:0:0:0:0
		else
		{
			memset(addr,0, 16);
			prefix_length = 0;
		}
	}
	
	
	//----------------------------------------------------------------------------
	
	void set_debug( Debug& debug )
	{
		debug_ = &debug;
	}
	
	// --------------------------------------------------------------------
	
	//NOTE This should be a configured address (u bit)
	void set_address( uint8_t* address, uint8_t prefix_l = 64 )
	{
		memcpy(&(addr[0]), address, 16);
		prefix_length = prefix_l;
	}
	
	// --------------------------------------------------------------------
	
	//If the prefix_l is shorter than 64, the prefix has to contain zeros at the lower bits!
	void set_prefix( uint8_t* prefix, uint8_t prefix_l = 64 )
	{	
		memcpy(&(addr[0]), prefix, (int)(prefix_l / 8));
		prefix_length = prefix_l;
	}
	
	// --------------------------------------------------------------------
	//Fix 8 bytes long hostID
	void set_hostID( uint8_t* host )
	{	
		memcpy(&(addr[8]), host, 8);
	}
	
	// --------------------------------------------------------------------
	
	void set_long_iid( link_layer_node_id_t* iid_, bool global )
	{
		link_layer_node_id_t iid = *iid_;
		//The different operation systems provide different length link_layer_node_id_t-s
		for ( unsigned int i = 0; i < ( sizeof(link_layer_node_id_t) ); i++ )
		{
			addr[15-i] = ( iid & 0xFF );
			iid = iid >> 8;
		}
		
		//addr[14] = (iid >> 40) & 0xFF;
		//addr[15] = (iid >> 32) & 0xFF;
		
		//If the provided link_layer address is short (uint16_t), the FFFE is included
		//Other bits are 0 --> PAN ID = 0
		/*if( sizeof(link_layer_node_id_t) < 3 )
		{
			addr[11] = 0xFF;
			addr[12] = 0xFE;
		}*/
		
		//Global address: u bit is 1
		if( global )
			addr[8] |= 0x02;
		//Local address: u bit is 0
		else
			addr[8] &= 0xFD;
	}
	
	//NOTE this is not used at the moment
	void set_short_iid( uint16_t iid, uint16_t pan_id = 0 )
	{
		addr[8] = (pan_id >> 8);
		
		//The u bit has to be 0
		//HACK
		//addr[8] &= 0xFD;
		addr[8] |= 0x02;
		
		addr[9] = (pan_id & 0x00FF);
		addr[10] = 0x00;

		addr[13] = 0x00;
		addr[14] = (iid >> 8);
		addr[15] = (iid & 0x00FF);
	}
	
	// --------------------------------------------------------------------
	
	void make_it_link_local()
	{
		uint8_t link_local_prefix[8];
		link_local_prefix[0]=0xFE;
		link_local_prefix[1]=0x80;
		memset(&(link_local_prefix[2]),0, 6);
		set_prefix(link_local_prefix);
		//delete global bit
		addr[8] &= 0xFD;
		prefix_length = 64;
	}
	
	// --------------------------------------------------------------------
	
	bool is_it_link_local( )
	{
		if ( (addr[0] == (uint8_t)0xFE) && (addr[1] == (uint8_t)0x80) )
		{
	 		for( int i = 2; i < 8; i++)
				if( addr[i] != 0 )
					return false;
		
			return true;
		}
		return false;
	}
	
	// --------------------------------------------------------------------
	
	void make_it_solicited_multicast( link_layer_node_id_t iid )
	{
		addr[0] = 0xFF;
		addr[1] = 0x02;
		memset(&(addr[2]), 0, 9);
		addr[11] = 0x01;
		addr[12] = 0xFF;
		
		if( sizeof( link_layer_node_id_t ) > 3 )
			addr[13] = iid >> 16;
		else
			addr[13] =  0x00;
		addr[14] = iid >> 8;
		addr[15] = iid;
		prefix_length = 104;
	}
	
	// --------------------------------------------------------------------
	
	char get_hex( uint8_t dec )
	{
		char c;
		if( dec < 10 )
			c = dec + 48;
		else
			c = dec + 55;
		
		return c;
	}

	char* get_address( char* str)
	{
		uint8_t zeros = 0;
		
		uint8_t act = 0;
		for( int i = 0; i < 16; i++ )
		{
			if( addr[i] == 0 )
				zeros++;
			
			str[act++] = get_hex( addr[i] >> 4 );
			str[act++] = get_hex( addr[i] & 0x0F );
			
			if(i%2==1 && i<15)
				str[act++] = ':';
		}
		
		if( zeros == 16 )
		{
			str[0] = ':';
			str[1] = ':';
			str[2] = '\0';
			return str;
		}
		
		str[act++] = '/';
		str[act++] = (prefix_length / 10) + 48;
		str[act++] = (prefix_length % 10) + 48;
		str[act++] = '\0';
		
		return str;
	}
	
	// --------------------------------------------------------------------
	
	bool operator ==(const IPv6Address<Radio, Debug>& b)
	{
		//If every byte is equal, return true
		if( common_prefix_length( b ) == 16 )
		{
			return true;
		}
		return false;
	}
	
	bool operator !=(const IPv6Address<Radio, Debug>& b)
	{
	 //If every byte is equal, return true
	 if( common_prefix_length( b ) != 16 )
	 {
	  return true;
	 }
	 return false;
	}
	
	// --------------------------------------------------------------------
	
	//Return the size of the same bytes at from the beginning of the address
	uint8_t common_prefix_length(const IPv6Address<Radio, Debug>& b )
	{
		uint8_t same = 0;
		for( int i = 0; i < 16; i++ )
		{
			if( addr[i] == b.addr[i] )
				same++;
			else
				break;
		}
		return same;
	}
	
	uint8_t addr[16];
	uint8_t prefix_length;
	private:
	
	Debug& debug()
	{ return *debug_; }
	
	
	typename Debug::self_pointer_t debug_;
   };
}
#endif
