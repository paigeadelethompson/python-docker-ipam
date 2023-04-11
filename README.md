# Overview
This is an IPAM driver plugin for Docker written in Python. 

- Allocation is persistent, using TinyDB and a table is created for each unique CIDR, as well as a separate JSON
database file (see TODO below for more information.)

- Docker networks can be created and deleted using this IPAM driver for both IPv4 and IPv6.

# Schema configuration
This IPAM driver is mainly schema driven. The idea is to create pools and to specify allocation preference tags to indicate which pools to draw from. Specific pools can be selected using the `scope_filter_tags` IPAM driver option with `docker network create`.

Here is an example schema that contains a root level IPv6 (ULA) pool `fc00:f00f::/32` and several definitions
for `/48` pools beneath it. This schema also contains a root level IPv4 pool `100.64.0.0/15` and several `/20`
defintions beneath it. For IPv6, each `/48` definition the child prefix designates a size of `/64`, which will
be the allocation size for requests to `request_pool` for `docker network create` however for address lease
requests to `request_address` for IPv6 a `/128` is given and a `/32` for IPv4 from the pool allocated by
`request_pool`:

```
{
    "schema_version": 1,
    "scopes": [{
        "network": "fc00:f00f::",
        "prefix": 32,
        "child_prefix": 48,
        "propagate_tags": true,
        "lock_down": true,
        "pre_seed_children": false,
        "tcp_ip_version": 6,
        "tags": [
            "python_docker_ipam_default"
        ],
        "scopes": [{
            "network": "fc00:f00f:0::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "null_routed",
                "default"
            ],
            "scopes": []
        }, {
            "network": "fc00:f00f:1::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "internally_routed"
            ],
            "scopes": []
        }, {
            "network": "fc00:f00f:2::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "ingress"
            ],
            "scopes": []
        }, {
            "network": "fc00:f00f:3::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "externally_routed",
                "egress",
                "ingress"
            ],
            "scopes": []
        }, {
            "network": "fc00:f00f:4::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "general_purpose"
            ],
            "scopes": []
        }, {
            "network": "fc00:f00f:5::",
            "child_prefix": 64,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "host_to_container"
            ],
            "scopes": []
        }]
    }, {
        "network": "100.64.0.0",
        "prefix": 17,
        "child_prefix": 20,
        "propagate_tags": true,
        "lock_down": true,
        "pre_seed_children": false,
        "tcp_ip_version": 4,
        "tags": [
            "python_docker_ipam_default"
        ],
        "scopes": [{
            "network": "100.64.0.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "null_routed",
                "default"
            ],
            "scopes": []
        }, {
            "network": "100.64.16.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "internally_routed"
            ],
            "scopes": []
        }, {
            "network": "100.64.32.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "ingress"
            ],
            "scopes": []
        }, {
            "network": "100.64.48.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "externally_routed",
                "egress",
                "ingress"
            ],
            "scopes": []
        }, {
            "network": "100.64.64.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "general_purpose"
            ],
            "scopes": []
        }, {
            "network": "100.64.80.0",
            "child_prefix": 30,
            "propagate_tags": true,
            "pre_seed_children": false,
            "tags": [
                "host_to_container"
            ],
            "scopes": []
        }]
    }]
}
```

This file should be named `schema.json` and mapped to the `/work` directory of the plugin container.

## Schema parameters
- TODO needs more documentation

# Usage

## Build
```
docker build -t python-docker-ipam-plugin -t python-docker-ipam-plugin:latest .
```

## Execution
```
docker run --rm -it -v $PWD:/work -v /run/docker/plugins:/run/docker/plugins python-docker-ipam-plugin:latest
```

## Usage
### IPv4
```
docker network create --ipam-driver pyipam test --ipam-opt "scope_filter_tags="null_routed"" --ipam-opt "id="testnet""

```

#### Verification
- `docker network inspect test`
```
[
    {
        "Name": "test",
        "Id": "91b51f494128608c606149e5cdb934e1b402df5f43c0d064725d3df75179fc29",
        "Created": "2020-07-17T13:21:46.123011013Z",
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv6": false,
        "IPAM": {
            "Driver": "pyipam",
            "Options": {
                "id": "testnet",
                "scope_filter_tags": "null_routed"
            },
            "Config": [
                {
                    "Subnet": "100.64.0.0/30",
                    "Gateway": "100.64.0.1"
                }
            ]
        },
        "Internal": false,
        "Attachable": false,
        "Ingress": false,
        "ConfigFrom": {
            "Network": ""
        },
        "ConfigOnly": false,
        "Containers": {},
        "Options": {},
        "Labels": {}
    }
]
```

### IPv6
```
docker network create --ipam-driver pyipam test6 --ipam-opt "scope_filter_tags="null_routed"" --ipam-opt "id="testnet"" --ipv6
```

#### Verification
- `docker network inspect test6`
```
[
    {
        "Name": "test6",
        "Id": "e4256519fd8f3b978063b152aacc63dd4ca27ee85816b02f3445878c4a29ed15",
        "Created": "2020-07-17T13:24:11.400720284Z",
        "Scope": "local",
        "Driver": "bridge",
        "EnableIPv6": true,
        "IPAM": {
            "Driver": "pyipam",
            "Options": {
                "id": "testnet",
                "scope_filter_tags": "null_routed"
            },
            "Config": [
                {
                    "Subnet": "100.64.0.4/30",
                    "Gateway": "100.64.0.5"
                },
                {
                    "Subnet": "fc00:f00f::/64",
                    "Gateway": "fc00:f00f::1/128"
                }
            ]
        },
        "Internal": false,
        "Attachable": false,
        "Ingress": false,
        "ConfigFrom": {
            "Network": ""
        },
        "ConfigOnly": false,
        "Containers": {},
        "Options": {},
        "Labels": {}
    }
]
```

#### Docker Compose
- Version 2.4 is required, > 2.4 is not currently supported.
```
version: "2.4"

networks:
  default:
    internal: true
    ipam:
      driver: pyipam
      options:
          id: "fluentd_default_net"
          scope_filter_tags: "host_to_container"
services:
  fluentd:
    hostname: fluentd
    domainname: docker.internal
    restart: unless-stopped
    image: fluentd
    networks:
      - default
```

## Development
```
docker run --rm -it -v $PWD:/work -v /run/docker/plugins:/run/docker/plugins python-docker-ipam-plugin:latest /bin/bash
pipenv shell
pipenv sync
pipenv run dev-server
```

# Implemented 
- scope persistence 
- scope factory; single unified database or one file per scope
- TinyDB; optionally MongoDB 
- Filter / selection tags

# TODO
- Docker swarm support; swarm is technically possible but should be revisted. Must be compatible with both VXLAN/eBGP and swarm mesh networking topologies
- Custom prefix length (deviation from schema)
- default behavior when no filter/select tags are specified

# Example of where it would be useful 
- Docker-ory; where it could be used instead of manually allocating networks to each network plane of containers (all that would be required is specifying a tag name; https://github.com/paigeadelethompson/docker-ory/blob/master/or_cockroach/docker-compose.yml#L3
