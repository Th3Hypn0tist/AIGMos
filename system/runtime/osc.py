from __future__ import annotations

from system.boot import boot_log

import socket
import struct
import threading
from typing import Any


class OSCInServer(threading.Thread):
    def __init__(self, bind_ip: str, port: int, buffer_size: int, adapter) -> None:
        super().__init__(daemon=True, name="osc")
        self.bind_ip = bind_ip
        self.port = int(port)
        self.buffer_size = int(buffer_size)
        self.adapter = adapter
        self._running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.bind_ip, self.port))
        self.sock.settimeout(0.2)
        boot_log(f"[osc-bind] {self.bind_ip}:{self.port} buffer={self.buffer_size}")

    def stop(self) -> None:
        self._running = False
        try:
            self.sock.close()
        except Exception:
            pass

    def run(self) -> None:
        boot_log("[osc-thread] started")
        while self._running:
            try:
                data, addr = self.sock.recvfrom(self.buffer_size)
                for address, args in decode_osc_packet(data):
                    self.adapter.apply_packet(address, args)
            except socket.timeout:
                continue
            except OSError:
                if not self._running:
                    break
                boot_log("[osc-error] socket closed unexpectedly")
            except Exception as e:
                boot_log(f"[osc-error] {type(e).__name__}: {e}")


def decode_osc_packet(data: bytes) -> list[tuple[str, list[Any]]]:
    if data.startswith(b"#bundle\x00"):
        return _decode_bundle(data)
    return [_decode_message(data)]


def _decode_bundle(data: bytes) -> list[tuple[str, list[Any]]]:
    offset = 16
    messages: list[tuple[str, list[Any]]] = []
    while offset < len(data):
        if offset + 4 > len(data):
            break
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        offset += 4
        chunk = data[offset:offset + size]
        offset += size
        if not chunk:
            continue
        messages.extend(decode_osc_packet(chunk))
    return messages


def _decode_message(data: bytes) -> tuple[str, list[Any]]:
    address, offset = _read_osc_string(data, 0)
    tags, offset = _read_osc_string(data, offset)
    if not tags.startswith(","):
        raise ValueError("invalid OSC type tag string")

    args: list[Any] = []
    for tag in tags[1:]:
        if tag == "i":
            _need(data, offset, 4)
            args.append(struct.unpack(">i", data[offset:offset + 4])[0])
            offset += 4
            continue
        if tag == "f":
            _need(data, offset, 4)
            args.append(struct.unpack(">f", data[offset:offset + 4])[0])
            offset += 4
            continue
        if tag == "s":
            value, offset = _read_osc_string(data, offset)
            args.append(value)
            continue
        if tag == "b":
            value, offset = _read_blob(data, offset)
            args.append(value)
            continue
        if tag == "T":
            args.append(True)
            continue
        if tag == "F":
            args.append(False)
            continue
        if tag == "N":
            args.append(None)
            continue
        if tag == "I":
            args.append(float("inf"))
            continue
        raise ValueError(f"unsupported OSC type tag: {tag}")

    return address, args


def _read_osc_string(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\x00", offset)
    if end == -1:
        raise ValueError("unterminated OSC string")
    value = data[offset:end].decode("utf-8")
    next_offset = _pad4(end + 1)
    if next_offset > len(data):
        raise ValueError("truncated OSC string")
    return value, next_offset


def _read_blob(data: bytes, offset: int) -> tuple[bytes, int]:
    _need(data, offset, 4)
    size = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    _need(data, offset, size)
    value = data[offset:offset + size]
    offset += size
    next_offset = _pad4(offset)
    if next_offset > len(data):
        raise ValueError("truncated OSC blob")
    return value, next_offset


def _need(data: bytes, offset: int, size: int) -> None:
    if offset + size > len(data):
        raise ValueError("truncated OSC packet")


def _pad4(value: int) -> int:
    return (value + 3) & ~3
