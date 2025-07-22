#!/bin/bash

echo "Adding local hostnames to /etc/hosts for HTTPS proxy setup..."
echo ""

# Check if entries already exist
if grep -q "authelia.localhost.local" /etc/hosts && grep -q "app.localhost.local" /etc/hosts && grep -q "api.localhost.local" /etc/hosts; then
    echo "Hostnames already exist in /etc/hosts"
else
    echo "Adding the following entries to /etc/hosts:"
    echo "127.0.0.1 authelia.localhost.local"
    echo "127.0.0.1 app.localhost.local"  
    echo "127.0.0.1 api.localhost.local"
    echo ""
    
    # Add entries to /etc/hosts
    echo "" | sudo tee -a /etc/hosts > /dev/null
    echo "# Refinance OIDC Development Setup" | sudo tee -a /etc/hosts > /dev/null
    echo "127.0.0.1 authelia.localhost.local" | sudo tee -a /etc/hosts > /dev/null
    echo "127.0.0.1 app.localhost.local" | sudo tee -a /etc/hosts > /dev/null
    echo "127.0.0.1 api.localhost.local" | sudo tee -a /etc/hosts > /dev/null
    
    echo "Hostnames added successfully!"
fi

echo ""
echo "Once hostnames are added, you can access:"
echo "- Authelia OIDC Provider: https://authelia.localhost.local"
echo "- UI Application: https://app.localhost.local"
echo "- API Backend: https://api.localhost.local"
echo ""
echo "Note: Your browser will show security warnings for self-signed certificates."
echo "Click 'Advanced' and 'Proceed to site' to continue."
