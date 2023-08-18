#!/usr/bin/env python3

# Override the default ulimit before doing anything else. This might not be required now but it's
# probably safer to just leave it in place. It was originally needed for the Borb pdf library but
# I've switched library now. I only seen this be an issue on macOS so the fix is specific to it
# for now. The new limit I've chosen was just one I found to be large enough that I didn't see
# any issues.
import resource
resource.setrlimit(resource.RLIMIT_NOFILE, (2048, 2048))


from genericpath import isfile
import autojimmy
import os

if __name__ == "__main__":
    # On macOS Python doesn't use the system certificate authority. Instead it uses its own ca
    # certificate installed by the certifi module. The problem is, on a system that doesn't have
    # Python installed the certificate won't be present so the application will fail to install. To
    # work around this I include the Python certificate with the application, this code sets
    # environment variables to make the application use the included copy of the certificate I
    # suspect there is a better way to do this but I don't know what it is.
    certPath = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'cert',
        'cacert.pem')
    if os.path.isfile(certPath):
        os.environ["SSL_CERT_FILE"] = certPath
        os.environ["REQUESTS_CA_BUNDLE"] = certPath

    autojimmy.main()
