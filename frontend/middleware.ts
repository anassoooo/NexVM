import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("myvms_token")?.value;
  const isAdmin = request.cookies.get("myvms_admin")?.value === "1";
  const { pathname } = request.nextUrl;

  const isAuthRoute = pathname === "/login" || pathname === "/signup";
  const isAdminRoute = pathname.startsWith("/admin");

  // Unauthenticated → login
  if (!token && !isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    return NextResponse.redirect(url);
  }

  // Already authenticated → skip auth pages
  if (token && isAuthRoute) {
    const url = request.nextUrl.clone();
    url.pathname = "/ai";
    url.search = "";
    return NextResponse.redirect(url);
  }

  // Non-admin blocked from /admin/*
  if (token && isAdminRoute && !isAdmin) {
    const url = request.nextUrl.clone();
    url.pathname = "/ai";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
