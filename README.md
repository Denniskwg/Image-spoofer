# IMAGE HASH SPOOFING
Image spoofing involves modifying an image in such a way that the visual appearance of the image created after modification appears identical to the original image but
when checksum of the two images is calculated, they yield different hash values. Cryptographic hashes like **sha256** are designed in a way that
a slight change in the input yields a totally different hash value that is unpredictable. Hence manipulating the hash is time consuming and requires intensive resourcesespecially if you want a hash with a specific value. sha256 algorithm is used for this solution.

This repository defines a tool spoof that takes an image and a hex string and yields an image *altered.png* that has a hash that starts with the hex string. The approach used is flipping the Least significant bit of the pixel data using parrarel processing(multithreading) until the desired hash value is achieved. The solution currently works with two digit strings, adding more digits would need more iterations.

# usage
- Clone the repository:
  ```bash
  git clone https://github.com/Denniskwg/Image-spoofer.git
- Install the package:
  ```bash
  pipx install git+https://github.com/Denniskwg/Image-spoofer.git

- Use it as:
   ```bash
  spoof 0x11 "image.png" "output_image.png"

- check if *output_image.png* matches the printed hash using sha256sum
