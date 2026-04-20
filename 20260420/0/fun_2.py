import asyncio
import fun_1


async def sqroot_echo(reader, writer):
    while data := await reader.readline():
        inp = data.strip().decode()
        try:
            res = fun_1.sqroots(inp)
        except ValueError as e:
            res = f"{e}"
        writer.write(f"{res}\n".encode())
    writer.close()
    await writer.wait_closed()


async def main():
    server = await asyncio.start_server(sqroot_echo, '0.0.0.0', 1337)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
