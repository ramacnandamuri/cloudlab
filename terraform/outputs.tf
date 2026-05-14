output "elastic_ip" {
  description = "Public IP of the webapp"
  value       = aws_eip.web.public_ip
}

output "webapp_url" {
  description = "URL to access the webapp"
  value       = "http://${aws_eip.web.public_ip}:3000"
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i ~/.ssh/cloudlab-key.pem ubuntu@${aws_eip.web.public_ip}"
}