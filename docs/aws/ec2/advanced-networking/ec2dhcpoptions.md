# AWS EC2DHCPOptions

EC2DHCPOptions represents a DHCP Options Set—a configuration that specifies how DNS resolution and NTP settings are handled for instances within a VPC. Custom DHCP options sets allow you to provide your own DNS servers, NTP servers, and domain names.

## Configuration

*   `vpcId` (string, required): VPC ID to associate with this DHCP options set.
*   `domainName` (string, optional): Domain name suffix for DNS queries.
*   `domainNameServers` (array of strings, optional): DNS servers (e.g., `["8.8.8.8", "8.8.4.4"]`).
*   `ntpServers` (array of strings, optional): NTP servers for time synchronization.
*   `netbiosNameServers` (array of strings, optional): NetBIOS name servers.
*   `netbiosNodeType` (integer, optional): NetBIOS node type (1-4).
*   `tags`, `syncedLabels`, `syncedAnnotations`: Metadata.

## Status Outputs

*   `status.dhcpOptionsId`: AWS-assigned DHCP options set identifier (format: `dopt-*`).
*   `status.associatedVpcs`: VPCs currently associated with this options set.

## Example EC2DHCPOptions

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2DHCPOptions
metadata:
  name: custom-dns-dhcp
  namespace: default
spec:
  vpcId: vpc-0123456789abcdef0
  domainName: "example.com"
  domainNameServers:
    - "10.0.0.2"     # On-premises DNS server
    - "8.8.8.8"      # Google DNS
  ntpServers:
    - "10.0.0.1"     # On-premises NTP server
    - "169.254.169.123"  # AWS NTP server
  tags:
    environment: production
    purpose: custom-dns
```

### On-Premises Integration

```yaml
apiVersion: aws.kropath.run/v1alpha1
kind: EC2DHCPOptions
metadata:
  name: hybrid-dhcp
  namespace: default
spec:
  vpcId: vpc-hybrid
  domainName: "corp.internal"
  domainNameServers:
    - "192.168.1.10"  # Corporate DNS
    - "192.168.1.11"
  ntpServers:
    - "192.168.1.5"   # Corporate NTP
```

## Naming

DHCP options sets have no user-assigned name. AWS assigns `dhcpOptionsId`.

See [EC2VPC](../networking-core/ec2vpc.md) for VPC configuration and [EC2 Family](../ec2.md) for related resources.
