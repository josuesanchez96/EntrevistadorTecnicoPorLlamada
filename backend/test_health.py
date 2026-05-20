import httpx
import asyncio

async def check_health():
    print("Checking backend health at http://localhost:8000/health ...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response JSON: {response.json()}")
    except Exception as e:
        import traceback
        print("Error connecting to backend:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_health())
