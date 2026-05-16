output "alb_dns" {
  description = "Load balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "webapp_url" {
  description = "URL to access the webapp"
  value       = "http://${aws_lb.main.dns_name}"
}

output "ssh_command" {
  description = "Command to SSH into instance 1"
  value       = "ssh -i ~/.ssh/cloudlab-key.pem ubuntu@${aws_eip.web.public_ip}"
}