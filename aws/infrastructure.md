# Week 4 - AWS Infrastructure

## Resources created
- VPC: 10.0.0.0/16 (eu-west-2)
- Public subnet: 10.0.1.0/24 (eu-west-2a)
- Internet Gateway: attached to VPC
- Route table: 0.0.0.0/0 → IGW
- Security group: ports 80, 3000 (public), 22 (my IP only)
- EC2: t4g.micro, Ubuntu 22.04 ARM64
- Docker: ramachaitanya/webapp:v2

## How to deploy
1. Launch EC2 with cloudlab-key
2. Install Docker
3. docker pull ramachaitanya/webapp:v2
4. docker run -d -p 3000:3000 webapp

## Live URL
http://18.175.217.45:3000
