network-diag git:(main) ✗ python -m backend.cli chat

Network Diagnostics Assistant
Checking LLM backends...

  ✓ ollama
  ✗ openai

Using model: auto
Type your network problem or 'quit' to exit.

--------------------------------------------------

You: my internet is not working. i am getting a no internet screen on chrome. Can you please help me diagnose it.

Thinking...

Running: check_adapter_status()
╭──────────────────────────────────────────────── check_adapter_status result ─────────────────────────────────────────────────╮
│ ## check_adapter_status Results                                                                                              │
│ **Status**: Success                                                                                                          │
│ **Platform**: macos                                                                                                          │
│                                                                                                                              │
│ ### Data                                                                                                                     │
│ - **adapters**: [{'name': 'lo0', 'display_name': 'lo0', 'status': 'up', 'type': 'loopback', 'mac_address': None, 'has_...    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Assistant

                                                  check_adapter_status Results                                                  

Status: ❌ FAIL Layer: OSI Layer 1-2 (Physical/Link) Finding:                                                                   

 • Your WiFi adapter (en0) is enabled (status: up), but it is not connected (is_connected: false).                              
 • The loopback interface (lo0) is connected but not relevant to external internet access.                                      
 • No active Ethernet connection is assigned an IP address (has_ip: false for all Ethernet interfaces).                         

Next Step:                                                                                                                      

 • Connect to your WiFi network (en0).                                                                                          
 • If you're using Ethernet, ensure the cable is plugged in and the switch/router is powered on.                                
 • After connecting, check if an IP address is assigned automatically.                                                          

Would you like me to proceed with checking your IP configuration after connecting?                                              

You: 