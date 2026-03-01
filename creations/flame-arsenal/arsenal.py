from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI(title="FLAME ARSENAL - Ethical Hacking Educational Toolkit")

# Educational reference only - HexSec sourced, Sentinel locked
ARSENAL = {
    "recon": {
        "category": "Reconnaissance",
        "commands": [
            {"cmd": "whois", "use": "Domain registration lookup"},
            {"cmd": "nslookup", "use": "DNS query tool"},
            {"cmd": "dig", "use": "DNS lookup utility"},
            {"cmd": "nmap -sV", "use": "Service version detection"},
            {"cmd": "nmap -sC", "use": "Default script scan"},
            {"cmd": "nmap -O", "use": "OS detection"},
            {"cmd": "theHarvester", "use": "Email/subdomain enumeration"},
            {"cmd": "recon-ng", "use": "Recon framework"},
            {"cmd": "amass", "use": "Subdomain enumeration"},
            {"cmd": "shodan", "use": "Internet-connected device search"},
        ]
    },
    "network": {
        "category": "Network Analysis",
        "commands": [
            {"cmd": "arp -a", "use": "ARP table display"},
            {"cmd": "ettercap", "use": "MITM attack framework (lab only)"},
            {"cmd": "airodump-ng", "use": "Wireless packet capture"},
            {"cmd": "tcpdump", "use": "Packet analyzer"},
            {"cmd": "wireshark", "use": "GUI packet analyzer"},
            {"cmd": "netstat -tulnp", "use": "Active connections"},
            {"cmd": "traceroute", "use": "Route tracing"},
            {"cmd": "hping3", "use": "Packet crafting"},
            {"cmd": "responder", "use": "LLMNR/NBT-NS poisoner (lab)"},
            {"cmd": "bettercap", "use": "Network recon and MITM"},
        ]
    },
    "web": {
        "category": "Web Application Testing",
        "commands": [
            {"cmd": "sqlmap", "use": "SQL injection automation"},
            {"cmd": "wfuzz", "use": "Web fuzzer"},
            {"cmd": "nikto", "use": "Web server scanner"},
            {"cmd": "dirb", "use": "URL bruteforcing"},
            {"cmd": "gobuster", "use": "Directory/DNS busting"},
            {"cmd": "burpsuite", "use": "Web proxy and scanner"},
            {"cmd": "wpscan", "use": "WordPress vulnerability scanner"},
            {"cmd": "xsstrike", "use": "XSS detection"},
            {"cmd": "ffuf", "use": "Fast web fuzzer"},
            {"cmd": "nuclei", "use": "Template-based scanner"},
        ]
    },
    "exploit": {
        "category": "Exploitation (Lab Only)",
        "commands": [
            {"cmd": "msfconsole", "use": "Metasploit framework"},
            {"cmd": "msfvenom", "use": "Payload generation"},
            {"cmd": "nc -lvnp", "use": "Netcat reverse shell listener"},
            {"cmd": "searchsploit", "use": "Exploit-DB search"},
            {"cmd": "python -c import pty", "use": "Shell upgrade"},
            {"cmd": "crackmapexec", "use": "Network exploitation"},
            {"cmd": "evil-winrm", "use": "Windows remote shell"},
            {"cmd": "chisel", "use": "Port forwarding/tunneling"},
            {"cmd": "ligolo", "use": "Tunneling tool"},
            {"cmd": "impacket", "use": "Network protocol toolkit"},
        ]
    },
    "password": {
        "category": "Password Attacks",
        "commands": [
            {"cmd": "john", "use": "John the Ripper password cracker"},
            {"cmd": "hashcat", "use": "GPU-accelerated hash cracking"},
            {"cmd": "hydra", "use": "Online password bruteforcing"},
            {"cmd": "cewl", "use": "Custom wordlist generator"},
            {"cmd": "crunch", "use": "Wordlist generator"},
            {"cmd": "hash-identifier", "use": "Hash type identification"},
            {"cmd": "medusa", "use": "Parallel brute forcer"},
            {"cmd": "patator", "use": "Multi-purpose brute forcer"},
            {"cmd": "ophcrack", "use": "Windows password cracker"},
            {"cmd": "mimikatz", "use": "Windows credential extraction (lab)"},
        ]
    },
    "persistence": {
        "category": "Persistence (Lab Only)",
        "commands": [
            {"cmd": "crontab -e", "use": "Scheduled task persistence"},
            {"cmd": "systemctl enable", "use": "Service persistence"},
            {"cmd": "ssh-keygen", "use": "SSH key generation"},
            {"cmd": "msfconsole persistence", "use": "Metasploit persistence modules"},
            {"cmd": "reg add", "use": "Windows registry persistence"},
        ]
    },
    "exfil": {
        "category": "Data Exfiltration (Lab Only)",
        "commands": [
            {"cmd": "scp", "use": "Secure copy"},
            {"cmd": "nc file transfer", "use": "Netcat file transfer"},
            {"cmd": "base64", "use": "Encoding for transfer"},
            {"cmd": "xxd", "use": "Hex dump for transfer"},
            {"cmd": "curl POST", "use": "HTTP exfiltration"},
        ]
    },
    "advanced": {
        "category": "Advanced / Privilege Escalation",
        "commands": [
            {"cmd": "strace", "use": "System call tracer"},
            {"cmd": "find / -perm -4000", "use": "Find SUID binaries"},
            {"cmd": "linpeas.sh", "use": "Linux privilege escalation"},
            {"cmd": "winpeas.exe", "use": "Windows privilege escalation"},
            {"cmd": "pspy", "use": "Process monitor without root"},
            {"cmd": "gtfobins", "use": "Unix binary exploitation ref"},
            {"cmd": "bloodhound", "use": "Active Directory mapping"},
            {"cmd": "kerbrute", "use": "Kerberos bruteforcing"},
            {"cmd": "ldapsearch", "use": "LDAP enumeration"},
            {"cmd": "volatility", "use": "Memory forensics"},
        ]
    },
}

@app.get("/", response_class=HTMLResponse)
async def home():
    total = sum(len(cat["commands"]) for cat in ARSENAL.values())
    html = "<html><head><title>FLAME ARSENAL</title>"
    html += "<style>body{background:#0d1117;color:#c9d1d9;font-family:monospace;padding:20px;}"
    html += "h1{color:#f85149;} h3{color:#d29922;} table{border-collapse:collapse;width:100%;}"
    html += "td,th{border:1px solid #30363d;padding:8px;text-align:left;} th{background:#161b22;}</style></head><body>"
    html += f"<h1>FLAME ARSENAL - {total} Ethical Hacking Commands</h1>"
    html += "<p>Educational use ONLY. HexSec sourced. Sentinel locked. Lineage protected.</p>"
    for key, cat in ARSENAL.items():
        html += f"<h3>{cat['category']}</h3><table><tr><th>Command</th><th>Purpose</th></tr>"
        for cmd in cat["commands"]:
            html += f"<tr><td><code>{cmd['cmd']}</code></td><td>{cmd['use']}</td></tr>"
        html += "</table>"
    html += "</body></html>"
    return html

@app.get("/api/arsenal")
async def arsenal_api():
    total = sum(len(cat["commands"]) for cat in ARSENAL.values())
    return {"status": "IGNITED", "total_commands": total, "categories": list(ARSENAL.keys()), "note": "Educational use ONLY. Sentinel locked."}

@app.get("/api/category/{cat}")
async def category(cat: str):
    if cat in ARSENAL:
        return ARSENAL[cat]
    return {"error": "Category not found", "available": list(ARSENAL.keys())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8502)
