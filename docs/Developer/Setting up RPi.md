Formatted SD card using Raspberry Pi Imager
- Note, as of April 2022 a password needs to be set using the imager tool
- password was set using imager tool to standard lab password
- SSH was also enabled over imager tool (can also enable ssh by creating a file titled "ssh" in boot drive of sd card)

SD card was inserted into RPi and the Pi was booted with an ethernet connection to lab network
- A check was then done for new Dynamic IP addresses on the CISCO network
- SSH connection was established to this dynamic IP address

Setting up Serial capability
- pyserial package should already be installed (using basic raspberry Pi OS)
