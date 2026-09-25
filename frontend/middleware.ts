import { NextRequest, NextResponse } from "next/server";

type VerifiedUser = { is_admin: boolean };

async function verifyToken(token: string): Promise<VerifiedUser | null> {
  const baseUrl = process.env.BACKEND_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) return null;

  try {
    const response = await fetch(`${baseUrl}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) return null;
    const user: unknown = await response.json();
    if (!user || typeof user !== "object" || typeof (user as VerifiedUser).is_admin !== "boolean") {
      return null;
    }
    return user as VerifiedUser;
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  const isPublicRoute = pathname === "/";
  const isAdminRoute = pathname === "/admin" || pathname.startsWith("/admin/");
  const token = request.cookies.get("nexvm_token")?.value;

  if (!token && (isAuthRoute || isPublicRoute)) return NextResponse.next();

  const user = token ? await verifyToken(token) : null;
  if (!user) {
    if (isAuthRoute || isPublicRoute) {
      const response = NextResponse.next();
      if (token) response.cookies.delete("nexvm_token");
      response.cookies.delete("nexvm_admin");
      return response;
    }

    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    const response = NextResponse.redirect(url);
    if (token) response.cookies.delete("nexvm_token");
    response.cookies.delete("nexvm_admin");
    return response;
  }

  if (isAuthRoute || isPublicRoute) {
    const url = request.nextUrl.clone();
    url.pathname = user.is_admin ? "/admin" : "/vms";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (isAdminRoute && !user.is_admin) {
    const url = request.nextUrl.clone();
    url.pathname = "/vms";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
