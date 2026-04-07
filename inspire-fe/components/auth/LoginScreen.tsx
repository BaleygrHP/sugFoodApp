"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import svgPaths from '../imports/svg-s1hpubzamr';
import imgContainer from '../../assets/login.png';
import Image from "next/image";
import { ensureGuestSession, loginWithEmail } from "@/lib/api";
import { toast } from "sonner";

export default function LoginForm() {
  const [email, setEmail] = useState("p@gmail.com");
  const [password, setPassword] = useState("1");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await loginWithEmail(email, email.split("@")[0]);
      router.push("/home");
    } catch (error: any) {
      toast.error(error.message || "Failed to sign in");
    } finally {
      setSubmitting(false);
    }
  };

  const handleContinueAsGuest = async () => {
    try {
      setSubmitting(true);
      await ensureGuestSession(email.split("@")[0] || "Guest");
      router.push("/home");
    } catch (error: any) {
      toast.error(error.message || "Failed to continue as guest");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
    <div className="content-stretch flex items-center justify-center min-h-screen size-full" data-name="Create Login Flow" style={{ backgroundImage: "linear-gradient(150.923deg, rgb(255, 247, 237) 0%, rgb(254, 242, 242) 100%)" }}>
      <div className="bg-white h-auto md:h-[588.266px] relative rounded-[24px] shadow-[21px_25px_50px_-12px_#fef7ed] shrink-0 w-full max-w-[1152px] mx-4" data-name="Container">
        <div className="bg-clip-padding border-0 border-[transparent] border-solid overflow-clip relative rounded-[inherit] size-full flex flex-col md:flex-row">
          {/* Left Side - Form */}
          <div className="w-full md:w-1/2 p-8 md:p-0 flex items-center justify-center">
            <div className="content-stretch flex flex-col gap-[8px] w-full max-w-[448px] px-4 md:px-8 py-8" data-name="Container">
              {/* Form */}
              <form onSubmit={handleSubmit} className="w-full relative" data-name="Form">
                {/* Heading */}
                <div className="mb-2" data-name="Heading 1">
                  <h1 className="font-['Arimo',sans-serif] text-neutral-950">Lunch Voter</h1>
                </div>

                {/* Paragraph */}
                <div className="mb-8" data-name="Paragraph">
                  <p className="font-['Arimo',sans-serif] text-[#4a5565]">Vote with your team to decide where to eat</p>
                </div>

                {/* Email Input */}
                <div className="mb-4 h-[50px] rounded-[3.35544e+07px] relative w-full" data-name="Email Input">
                  <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="content-stretch flex items-center overflow-clip px-[24px] py-[12px] rounded-[inherit] size-full font-['Arimo',sans-serif] text-[16px] border border-[#d1d5dc] focus:outline-none focus:ring-2 focus:ring-[#ff8904] focus:border-transparent"
                  />
                </div>

                {/* Password Input Container */}
                <div className="mb-4 h-[50px] relative w-full" data-name="Container">
                  <div className="h-[50px] rounded-[3.35544e+07px] relative w-full" data-name="Password Input">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className="content-stretch flex items-center overflow-clip px-[24px] py-[12px] rounded-[inherit] size-full font-['Arimo',sans-serif] text-[16px] border border-[#d1d5dc] focus:outline-none focus:ring-2 focus:ring-[#ff8904] focus:border-transparent"
                    />
                  </div>
                  
                  {/* Eye Icon Button */}
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute content-stretch flex flex-col items-start right-[20px] size-[20px] top-[15px] cursor-pointer"
                    data-name="Button"
                  >
                    <div className="h-[20px] overflow-clip relative shrink-0 w-full" data-name="Icon">
                      <div className="absolute inset-[20.84%_8.33%]" data-name="Vector">
                        <div className="absolute inset-[-7.14%_-5%]">
                          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19 14">
                            <path d={svgPaths.pcb0000} stroke="#99A1AF" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" />
                          </svg>
                        </div>
                      </div>
                      {!showPassword && (
                        <div className="absolute inset-[37.5%]" data-name="Vector">
                          <div className="absolute inset-[-16.67%]">
                            <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7 7">
                              <path d={svgPaths.p2314a170} stroke="#99A1AF" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" />
                            </svg>
                          </div>
                        </div>
                      )}
                    </div>
                  </button>
                </div>

                {/* Remember & Forgot Password Container */}
                <div className="content-stretch flex items-center justify-between w-full mb-6" data-name="Container">
                  {/* Remember Checkbox */}
                  <label className="flex items-center gap-2 cursor-pointer" data-name="Label">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-300 text-[#ff8904] focus:ring-[#ff8904]"
                    />
                    <span className="font-['Arimo',sans-serif] text-[#364153] text-[14px]">Remember for 30 days</span>
                  </label>

                  {/* Forgot Password Link */}
                  <a href="#" className="font-['Arimo',sans-serif] text-[#4a5565] text-[14px] hover:underline" data-name="Link">
                    Forgot password?
                  </a>
                </div>

                {/* Log In Button */}
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-gradient-to-r from-[#ff8904] to-[#ff6900] h-[48px] rounded-[3.35544e+07px] shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1),0px_2px_4px_-2px_rgba(0,0,0,0.1)] w-full mb-6 hover:shadow-lg transition-all"
                  data-name="Button"
                >
                  <p className="font-['Arimo',sans-serif] text-[16px] text-center text-white">
                    {submitting ? "Signing in..." : "Log In"}
                  </p>
                </button>

                <button
                  type="button"
                  onClick={handleContinueAsGuest}
                  disabled={submitting}
                  className="w-full mb-6 border border-[#d1d5dc] h-[48px] rounded-[3.35544e+07px] hover:bg-[#f8fafc] transition-all"
                >
                  <p className="font-['Arimo',sans-serif] text-[16px] text-center text-[#101828]">
                    Continue as Guest
                  </p>
                </button>

                {/* Sign Up Link */}
                <div className="text-center w-full" data-name="Paragraph">
                  <p className="font-['Arimo',sans-serif] text-[#4a5565] text-[14px] inline">
                    Don&apos;t have an account?
                    <a href="#" className="font-['Arimo',sans-serif] text-[#101828] hover:underline" data-name="Link">
                      Sign Up
                    </a>
                  </p>
                </div>
              </form>
            </div>
          </div>

          {/* Right Side - Image */}
          <div className="hidden md:block w-1/2 h-[588.266px] relative overflow-clip" data-name="Container">
            <div className="absolute inset-0" data-name="Container">
              <Image
                src={imgContainer}
                alt="Street food"
                fill
                priority
                className="object-cover object-center pointer-events-none"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
