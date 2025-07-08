resource "aws_eip" "vm_eip" {
  domain = "vpc"
  tags = {
    Name = "vm_eip_monitoring"
  }
}

resource "aws_eip_association" "eip_assoc" {
  instance_id   = aws_instance.monitoring.id
  allocation_id = aws_eip.vm_eip.id
}