"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

const Spinner = () => (
  <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
);

export default function Viewer() {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 2000);

    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-white bg-opacity-80 backdrop-blur-sm flex justify-center items-center">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          backgroundImage: 'url("/street.png")',
          width: "100%",
          height: "100vh",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      >
        <Link href="/">
          <button className="bg-white p-3 rounded-xl ml-5 mt-5 hover:bg-gray-100">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18 18 6M6 6l12 12"
              />
            </svg>
          </button>
        </Link>
        <div className="flex justify-between items-center px-8 mt-64">
          <button
            className="rounded-full p-5 bg-blue-500 hover:bg-blue-600 active:shadow-none transition-shadow duration-150"
            style={{ boxShadow: "0px 4px 0px 0px rgba(120, 189, 251, 1)" }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6 text-white font-bold"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6.75 15.75 3 12m0 0 3.75-3.75M3 12h18"
              />
            </svg>
          </button>
          <button
            className="rounded-full p-5 bg-blue-500 hover:bg-blue-600 active:shadow-none transition-shadow duration-150"
            style={{ boxShadow: "0px 4px 0px 0px rgba(120, 189, 251, 1)" }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6 text-white font-bold"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.25 8.25 21 12m0 0-3.75 3.75M21 12H3"
              />
            </svg>
          </button>
        </div>
        <div className="flex justify-center items-center px-8 mt-64">
          <button
            className="rounded-full pl-5 pr-5 pt-4 pb-4 bg-blue-500 hover:bg-blue-600 active:shadow-none transition-shadow duration-150"
            style={{ boxShadow: "0px 6px 0px 0px rgba(120, 189, 251, 1)" }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="size-6 text-white font-bold"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M8.25 6.75 12 3m0 0 3.75 3.75M12 3v18"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
