import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null);

  if (
    !payload ||
    typeof payload.name !== "string" ||
    typeof payload.email !== "string" ||
    typeof payload.message !== "string"
  ) {
    return NextResponse.json(
      { ok: false, error: "Invalid contact payload." },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}
