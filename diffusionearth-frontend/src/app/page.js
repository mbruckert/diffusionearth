"use client";
import React, { useState } from "react";

export default function Home() {
  const morphs = [
    // First shape
    `M0.412,0.004 C0.496,0.007,0.579,0.033,0.651,0.075 C0.72,0.115,0.789,0.168,0.818,0.241 C0.845,0.312,0.772,0.395,0.802,0.466 C0.839,0.556,0.992,0.584,1,0.681 C1,0.765,0.907,0.827,0.835,0.876 C0.77,0.921,0.687,0.925,0.61,0.948 C0.544,0.968,0.482,1,0.412,1 C0.343,0.998,0.292,0.943,0.228,0.919 C0.158,0.893,0.057,0.915,0.017,0.855 C-0.025,0.791,0.039,0.709,0.039,0.634 C0.039,0.576,0.022,0.522,0.018,0.465 C0.013,0.391,-0.015,0.315,0.011,0.244 C0.038,0.169,0.095,0.102,0.166,0.06 C0.238,0.017,0.327,0.002,0.412,0.004`,
    // Second shape
    `M0.545,0.068 C0.618,0.064,0.684,-0.011,0.756,0.008 C0.826,0.027,0.873,0.1,0.91,0.166 C0.945,0.229,0.959,0.302,0.963,0.375 C0.966,0.442,0.926,0.504,0.93,0.572 C0.937,0.673,1,0.768,0.997,0.863 C0.967,0.948,0.863,0.982,0.78,1 C0.701,1,0.622,0.985,0.545,0.963 C0.48,0.945,0.424,0.909,0.362,0.883 C0.296,0.854,0.223,0.845,0.167,0.8 C0.104,0.749,0.046,0.685,0.02,0.605 C-0.007,0.524,0.006,0.434,0.019,0.349 C0.032,0.26,0.035,0.157,0.097,0.096 C0.161,0.034,0.259,0.037,0.344,0.032 C0.413,0.028,0.476,0.072,0.545,0.068`,
    // Third shape
    `M0.513,0.017 C0.582,0.034,0.629,0.094,0.689,0.132 C0.742,0.166,0.803,0.186,0.849,0.229 C0.898,0.276,0.939,0.329,0.965,0.392 C0.992,0.459,1,0.531,1,0.603 C0.997,0.683,0.987,0.765,0.946,0.834 C0.902,0.906,0.843,0.985,0.76,1 C0.672,1,0.599,0.93,0.513,0.908 C0.449,0.892,0.384,0.902,0.32,0.888 C0.244,0.871,0.157,0.87,0.099,0.819 C0.04,0.767,-0.005,0.686,0.002,0.609 C0.009,0.528,0.096,0.48,0.135,0.408 C0.162,0.356,0.174,0.299,0.196,0.245 C0.226,0.173,0.224,0.078,0.288,0.033 C0.349,-0.012,0.439,-0.001,0.513,0.017`,
    // Fourth shape
    `M0.483,0.027 C0.536,0.045,0.571,0.112,0.626,0.124 C0.708,0.141,0.804,0.054,0.872,0.108 C0.933,0.156,0.896,0.271,0.917,0.352 C0.939,0.438,1,0.511,1,0.601 C0.991,0.69,0.938,0.776,0.871,0.821 C0.803,0.866,0.716,0.821,0.64,0.842 C0.583,0.858,0.539,0.907,0.483,0.929 C0.411,0.957,0.325,1,0.263,0.989 C0.195,0.932,0.248,0.798,0.218,0.708 C0.199,0.649,0.151,0.612,0.121,0.56 C0.078,0.488,0.007,0.427,0.001,0.339 C-0.004,0.253,0.037,0.167,0.091,0.106 C0.143,0.047,0.22,0.026,0.292,0.011 C0.356,-0.001,0.421,0.006,0.483,0.027`,
    // Fifth shape
    `M0.525,0.091 C0.604,0.081,0.669,-0.005,0.748,0.006 C0.826,0.018,0.906,0.074,0.942,0.152 C0.978,0.231,0.928,0.327,0.938,0.415 C0.947,0.493,1,0.566,0.995,0.639 C0.967,0.715,0.856,0.707,0.809,0.771 C0.763,0.833,0.795,0.954,0.731,0.994 C0.67,1,0.596,0.954,0.525,0.95 C0.458,0.946,0.395,0.98,0.329,0.972 C0.248,0.962,0.141,0.974,0.097,0.899 C0.051,0.819,0.143,0.713,0.125,0.621 C0.108,0.531,0.002,0.479,0.001,0.387 C-0.001,0.299,0.06,0.221,0.119,0.161 C0.175,0.104,0.25,0.072,0.325,0.059 C0.392,0.047,0.457,0.099,0.525,0.091`,
  ];

  const duration = 10;
  const height = 400;
  const paths = morphs;
  const width = 400;

  const generateLinearKeySplines = () => {
    return paths.reduce((accumulator) => `${accumulator}0 0 1 1;`, "");
  };

  const generateValues = () => {
    const reversed = [...paths].reverse();
    reversed.shift();
    return [...paths, ...reversed].join(";");
  };

  const MorphingBlob = () => (
    <>
      <svg
        className="svg"
        style={{ position: "absolute", width: 0, height: 0 }}
      >
        <clipPath id="morph-clip-path-1" clipPathUnits="objectBoundingBox">
          <path d={paths[0]}>
            <animate
              attributeType="XML"
              attributeName="d"
              values={generateValues()}
              keySplines={generateLinearKeySplines()}
              dur={`${duration}s`}
              repeatCount="indefinite"
              fill="freeze"
              calcMode="linear"
            />
          </path>
        </clipPath>
      </svg>
      <div
        className="absolute"
        style={{
          height: `${height}px`,
          width: `${width}px`,
          clipPath: "url(#morph-clip-path-1)",
          backgroundImage: 'url("/points.png")',
          backgroundSize: "cover",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
        }}
      />
    </>
  );

  const [fileName, setFileName] = useState("");
  const [portalReady, setPortalReady] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [backgroundImage, setBackgroundImage] = useState('url("/street.png")');

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setFileName(file.name);
      const reader = new FileReader();
      reader.onload = (e) => {
        setUploadedImage(e.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSimulate = () => {
    if (uploadedImage) {
      setBackgroundImage(`url(${uploadedImage})`);
    }
    setPortalReady(true);
  };

  return (
    <div className="flex flex-wrap h-screen">
      <div className="w-full md:w-1/2 pr-8 md:pr-64 bg-gray-100 pt-6 px-8 border-r border-gray-300 h-full overflow-y-auto">
        <img src="/logo.png" alt="logo" className="w-20 h-20" />
        <h1 className="text-3xl font-semibold mt-4">Diffusion Earth</h1>
        <p className="text-xl">The world, if it was created by AI.</p>
        <div className="mt-4 flex items-center gap-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-5 h-5 text-gray-600"
          >
            <path
              fillRule="evenodd"
              d="m11.54 22.351.07.04.028.016a.76.76 0 0 0 .723 0l.028-.015.071-.041a16.975 16.975 0 0 0 1.144-.742 19.58 19.58 0 0 0 2.683-2.282c1.944-1.99 3.963-4.98 3.963-8.827a8.25 8.25 0 0 0-16.5 0c0 3.846 2.02 6.837 3.963 8.827a19.58 19.58 0 0 0 2.682 2.282 16.975 16.975 0 0 0 1.145.742ZM12 13.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
              clipRule="evenodd"
            />
          </svg>
          <span className="font-bold text-xl text-gray-600">Address</span>
        </div>
        <input
          className="border border-gray-300 rounded-lg p-2 mt-2 w-full"
          placeholder="Enter any address here..."
        />
        <hr className="my-4 border-gray-300" />
        <div className="mt-4 flex items-center gap-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-5 h-5 text-gray-600"
          >
            <path
              fillRule="evenodd"
              d="M1.5 6a2.25 2.25 0 0 1 2.25-2.25h16.5A2.25 2.25 0 0 1 22.5 6v12a2.25 2.25 0 0 1-2.25 2.25H3.75A2.25 2.25 0 0 1 1.5 18V6ZM3 16.06V18c0 .414.336.75.75.75h16.5A.75.75 0 0 0 21 18v-1.94l-2.69-2.689a1.5 1.5 0 0 0-2.12 0l-.88.879.97.97a.75.75 0 1 1-1.06 1.06l-5.16-5.159a1.5 1.5 0 0 0-2.12 0L3 16.061Zm10.125-7.81a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Z"
              clipRule="evenodd"
            />
          </svg>

          <span className="font-bold text-xl text-gray-600">Image</span>
        </div>
        <div className="mt-4">
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="bg-gray-200 p-4 rounded-lg flex gap-4 border border-gray-300 hover:bg-gray-300 transition-colors">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="currentColor"
                className="w-6 h-6"
              >
                <path
                  fillRule="evenodd"
                  d="M11.47 2.47a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06l-3.22-3.22V16.5a.75.75 0 0 1-1.5 0V4.81L8.03 8.03a.75.75 0 0 1-1.06-1.06l4.5-4.5ZM3 15.75a.75.75 0 0 1 .75.75v2.25a1.5 1.5 0 0 0 1.5 1.5h13.5a1.5 1.5 0 0 0 1.5-1.5V16.5a.75.75 0 0 1 1.5 0v2.25a3 3 0 0 1-3 3H5.25a3 3 0 0 1-3-3V16.5a.75.75 0 0 1 .75-.75Z"
                  clipRule="evenodd"
                />
              </svg>
              <h2>
                {fileName
                  ? `File selected: ${fileName}`
                  : "Upload an Image (Click or Drag Here)"}
              </h2>
            </div>
          </label>
          <input
            id="file-upload"
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept="image/*"
          />
        </div>
        <hr className="my-4 border-gray-300" />
        <div className="mt-4 flex items-center gap-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-5 h-5 text-gray-600"
          >
            <path d="M21.731 2.269a2.625 2.625 0 0 0-3.712 0l-1.157 1.157 3.712 3.712 1.157-1.157a2.625 2.625 0 0 0 0-3.712ZM19.513 8.199l-3.712-3.712-8.4 8.4a5.25 5.25 0 0 0-1.32 2.214l-.8 2.685a.75.75 0 0 0 .933.933l2.685-.8a5.25 5.25 0 0 0 2.214-1.32l8.4-8.4Z" />
            <path d="M5.25 5.25a3 3 0 0 0-3 3v10.5a3 3 0 0 0 3 3h10.5a3 3 0 0 0 3-3V13.5a.75.75 0 0 0-1.5 0v5.25a1.5 1.5 0 0 1-1.5 1.5H5.25a1.5 1.5 0 0 1-1.5-1.5V8.25a1.5 1.5 0 0 1 1.5-1.5h5.25a.75.75 0 0 0 0-1.5H5.25Z" />
          </svg>

          <span className="font-bold text-xl text-gray-600">Prompt</span>
        </div>
        <textarea
          className="border border-gray-300 rounded-lg p-2 mt-2 w-full"
          placeholder="Describe where you want your world to start..."
        />
        <hr className="my-4 border-gray-300" />
        <button
          className="bg-blue-500 text-white rounded-lg p-2 w-full font-bold hover:bg-blue-400"
          onClick={handleSimulate}
        >
          Simulate Location
        </button>
        {portalReady && (
          <div className="flex gap-4 mt-6">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              stroke-width="1.5"
              stroke="currentColor"
              class="size-6 text-green-500 "
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
              />
            </svg>
            <p className="text-green-500 font-bold">Portal is ready!</p>
          </div>
        )}
      </div>
      <div
        className="w-full md:w-1/2 h-full overflow-hidden pt-20 px-8 relative"
        style={{
          backgroundImage: backgroundImage,
          backgroundSize: "cover",
          opacity: 0.8,
        }}
      >
        <div className="absolute inset-0 bg-black opacity-50" />
        <div className="relative z-10 w-full h-full flex flex-col items-center justify-center">
          <MorphingBlob />
          {portalReady && (
            <div className="absolute inset-0 flex items-center justify-center">
              <button className="bg-white rounded-lg p-2 w-1/4 font-bold hover:bg-blue-100 text-blue-500 transition-colors duration-300 flex items-center justify-center gap-3">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-5"
                >
                  <path
                    fillRule="evenodd"
                    d="M15 3.75a.75.75 0 0 1 .75-.75h4.5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0V5.56l-3.97 3.97a.75.75 0 1 1-1.06-1.06l3.97-3.97h-2.69a.75.75 0 0 1-.75-.75Zm-12 0A.75.75 0 0 1 3.75 3h4.5a.75.75 0 0 1 0 1.5H5.56l3.97 3.97a.75.75 0 0 1-1.06 1.06L4.5 5.56v2.69a.75.75 0 0 1-1.5 0v-4.5Zm11.47 11.78a.75.75 0 1 1 1.06-1.06l3.97 3.97v-2.69a.75.75 0 0 1 1.5 0v4.5a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h2.69l-3.97-3.97Zm-4.94-1.06a.75.75 0 0 1 0 1.06L5.56 19.5h2.69a.75.75 0 0 1 0 1.5h-4.5a.75.75 0 0 1-.75-.75v-4.5a.75.75 0 0 1 1.5 0v2.69l3.97-3.97a.75.75 0 0 1 1.06 0Z"
                    clipRule="evenodd"
                  />
                </svg>
                Open Portal
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
