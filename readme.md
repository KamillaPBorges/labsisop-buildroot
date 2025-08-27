## Mapeamento dos campos ⇄ /proc e /sys

| Campo JSON                         | Fonte (/proc ou /sys)                                    | Como extrair / Observações |
|-----------------------------------|-----------------------------------------------------------|----------------------------|
| `datetime`                        | — (biblioteca `datetime` do Python)                      | `datetime.now().isoformat()`; não vem de /proc. |
| `uptime_seconds`                  | `/proc/uptime`                                           | Primeiro número (segundos desde o boot). |
| `cpu.model`                       | `/proc/cpuinfo`                                          | Linha `model name` (ou `Hardware`/`Processor` em algumas archs). |
| `cpu.speed_mhz`                   | `/proc/cpuinfo`                                          | Linha `cpu MHz` (converter para `float`). |
| `cpu.usage_percent`               | `/proc/stat`                                             | Calcular a partir de duas leituras do agregado `cpu` (user,nice,system,idle,iowait,irq,softirq,steal). `%uso = 100*(Δtotal - Δidle)/Δtotal`. |
| `memory.total_mb`                 | `/proc/meminfo`                                          | Linha `MemTotal` (kB → MB). |
| `memory.used_mb`                  | `/proc/meminfo`                                          | `used = MemTotal - MemAvailable` (ambos em kB → MB). |
| `os_version`                      | `/proc/version`                                          | Conteúdo inteiro (string). Alternativa: `/proc/sys/kernel/{osrelease,version}`. |
| `processes[] .pid`                | `/proc/<pid>/`                                           | Diretórios numéricos em `/proc` são PIDs. |
| `processes[] .name`               | `/proc/<pid>/comm`                                       | Conteúdo é o nome curto do processo (fazer `strip()`); fallback: `/proc/<pid>/stat` campo 2. |
| `disks[] .device`                 | `/proc/partitions`                                       | Coluna do nome do dispositivo (ex.: `sda`, `vda`, `mmcblk0`). |
| `disks[] .size_mb`                | `/proc/partitions`                                       | Coluna “blocks” (blocos de 1 KiB na maioria dos kernels) → MB. |
| `usb_devices[] .port`             | `/sys/bus/usb/devices/*/busnum`                          | Convertido para string; pode combinar com `devpath` ou caminho do nó. |
| `usb_devices[] .description`      | `/sys/bus/usb/devices/*/product`                         | Nome do produto; fallback: `manufacturer` + `idVendor:idProduct`. |
| `network_adapters[] .interface`   | `/sys/class/net/`                                        | Nome de cada interface (ex.: `eth0`, `lo`). |
| `network_adapters[] .ip_address`  | `/proc/net/fib_trie` **ou** `/proc/net/route` + `ioctl`  | Maneiras simples: 1) parsear `fib_trie` para IPv4 local, 2) abrir socket e usar `SIOCGIFADDR` por interface. Evitar libs externas. |
