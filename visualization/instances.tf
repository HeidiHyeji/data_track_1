resource "aws_key_pair" "monitoring_key" {
  key_name   = "monitoring_key"
  public_key = file(var.PATH_TO_PUBLIC_KEY)
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_instance" "monitoring" {
  ami           = lookup(var.AMIS, var.AWS_REGION)
  instance_type = "t2.large"
  key_name      = aws_key_pair.monitoring_key.key_name
  vpc_security_group_ids = [aws_security_group.allow_monitoring.id]
  root_block_device{
    volume_size   = 30
  }
  
  provisioner "file" {
    source      = "script.sh"
    destination = "/tmp/script.sh"
  }
  provisioner "grafana_installer" {
    source      = "install_grafana.sh"
    destination = "/tmp/install_grafana.sh"
  }
  provisioner "grafana_dashboard" {
    source      = "import_dashboard.sh"
    destination = "/tmp/import_dashboard.sh"
  }
  provisioner "promconfig" {
    source      = "prometheus.yml"
    destination = "/tmp/prometheus.yml"
  }
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/script.sh",
      "sudo /tmp/script.sh"
    ]
  }
  provisioner "remote-exec-grafana-install" {
    inline = [
      "chmod +x /tmp/install_grafana.sh",
      "sudo /tmp/install_grafana.sh"
    ]
  }
  provisioner "remote-exec-grafana-dashboard" {
    inline = [
      "chmod +x /tmp/install_grafana.sh",
      "sudo /tmp/install_grafana.sh"
    ]
  }
  connection {
    host        = coalesce(self.public_ip, self.private_ip)
    user        = var.INSTANCE_USERNAME
    private_key = file(var.PATH_TO_PRIVATE_KEY)
  }

  tags = {
    Name        = "m1"
  }
}
