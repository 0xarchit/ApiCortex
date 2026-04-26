import httpx
import json
import asyncio

# By default, hitting the Rust microservice directly.
# If testing via the control-plane, change this URL to http://127.0.0.1:8000/api/v1/testing/execute
# and add your JWT token to the headers.
EXECUTOR_URL = "http://127.0.0.1:9090/v1/execute"

async def execute_test(name: str, payload: dict):
    print(f"\n{'='*50}")
    print(f"🚀 Running: {name}")
    print(f"{'='*50}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(EXECUTOR_URL, json=payload, timeout=20.0)
            
            if response.status_code != 200:
                print(f"❌ Error: Received status {response.status_code}")
                print(response.text)
                return

            result = response.json()
            if not result.get("success"):
                print(f"❌ Execution failed: {result.get('error')}")
                return

            data = result.get("result", {})
            diagnostics = data.get("diagnostics", {})

            print(f"✅ Protocol: {payload.get('protocol').upper()}")
            
            if payload.get("protocol") in ["http", "graphql"]:
                print(f"📡 Target: {payload.get('method', 'GET')} {payload.get('url')}")
                print(f"📥 Status: {data.get('status_code')}")
                print(f"⏱️  Total Time: {diagnostics.get('total_time_ms', 0):.2f} ms")
                print(f"⏱️  DNS: {diagnostics.get('dns_resolution_time_ms', 0):.2f} ms")
                print(f"⏱️  TTFB: {diagnostics.get('time_to_first_byte_ms', 0):.2f} ms")
                
                # Preview body
                body = data.get("body")
                if isinstance(body, dict) or isinstance(body, list):
                    body_str = json.dumps(body, indent=2)
                else:
                    body_str = str(body)
                print(f"\n📦 Body Preview (first 250 chars):\n{body_str[:250]}...")
            
            elif payload.get("protocol") == "websocket":
                print(f"📡 Target: WS {payload.get('url')}")
                print(f"⏱️  Total Session Time: {data.get('total_time_ms', 0):.2f} ms")
                messages = data.get("messages", [])
                print(f"📩 Messages Received: {len(messages)}")
                for msg in messages:
                    print(f"   [{msg['received_at_ms']:.2f}ms] {msg['data'][:100]}")
                    
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

async def main():
    # 1. REST GET Request
    await execute_test("1. REST GET", {
        "protocol": "http",
        "method": "GET",
        "url": "https://jsonplaceholder.typicode.com/posts/1",
        "headers": {
            "User-Agent": "ApiCortex-Testing/1.0"
        }
    })

    # 2. REST POST Request
    await execute_test("2. REST POST (JSON)", {
        "protocol": "http",
        "method": "POST",
        "url": "https://httpbin.org/post",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": {
            "title": "foo",
            "body": "bar",
            "userId": 1
        }
    })

    # 3. GraphQL Public API
    await execute_test("3. GraphQL Query (Countries API)", {
        "protocol": "graphql",
        "url": "https://countries.trevorblades.com/",
        "body": {
            "query": """
            query {
              country(code: "BR") {
                name
                native
                capital
                currency
                languages {
                  code
                  name
                }
              }
            }
            """
        }
    })

    # 4. WebSocket (Single Message Echo)
    await execute_test("4. WebSocket (Single Strategy)", {
        "protocol": "websocket",
        "url": "wss://echo.websocket.org/",
        "ws_config": {
            "initial_message": "Hello from ApiCortex!",
            "strategy": "single",
            "timeout_ms": 5000
        }
    })

    # 5. WebSocket (Duration Strategy)
    await execute_test("5. WebSocket (Duration Strategy)", {
        "protocol": "websocket",
        "url": "wss://echo.websocket.org/",
        "ws_config": {
            "strategy": "duration",
            "listen_duration_ms": 2000
        }
    })

    # 6. WebSocket (Count Strategy)
    await execute_test("6. WebSocket (Count Strategy)", {
        "protocol": "websocket",
        "url": "wss://echo.websocket.org/",
        "ws_config": {
            "initial_message": "Echo me",
            "strategy": "count",
            "message_count": 2,
            "timeout_ms": 8000
        }
    })

if __name__ == "__main__":
    asyncio.run(main())
