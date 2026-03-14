import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const accessToken = request.cookies.get("acx_access")?.value;
  const refreshToken = request.cookies.get("acx_refresh")?.value;
  const token = accessToken || refreshToken;
  const isAuthPage = request.nextUrl.pathname.startsWith("/login");
  const isPublicPage = request.nextUrl.pathname === "/";

  if (!token && !isAuthPage && !isPublicPage) {
    // Redirect unauthenticated users to login
    return NextResponse.redirect(new URL("/login", request.url));
  }

  if (token && isAuthPage) {
    // Redirect authenticated users away from login
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, sitemap.xml, robots.txt (metadata files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
