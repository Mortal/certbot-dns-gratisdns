GratisDNS DNS Authenticator plugin for Certbot
==============================================

Create a text file with the following content:

```
# GratisDNS credentials used by Certbot
certbot_dns_gratisdns:dns_gratisdns_username = example
certbot_dns_gratisdns:dns_gratisdns_password = hunter2
certbot_dns_gratisdns:dns_gratisdns_otp_secret = GE4GMZJSGNRTCNJSGEZDKYZYGEZGEYZXGU3TIYRXMZTGCODFGRQWMOBSGYYDEYTE
```

Run the following command: `sudo certbot certonly -d \*.example.com -d example.com -a certbot-dns-gratisdns:dns-gratisdns`

When prompted for the config file, enter the path to the above text file.

About
-----

This plugin is a fork of `certbot_dns_gehirn`.
The logic is based on [`acme.sh_dns_gratisdns`](https://github.com/zylopfa/acme.sh_dns_gratisdns).
