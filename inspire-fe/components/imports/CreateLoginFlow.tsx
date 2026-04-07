import svgPaths from "./svg-s1hpubzamr";
import imgContainer from "figma:asset/a5a72968952a57b811830c9a36b9e06cb7357539.png";
import Image from "next/image";
function Checkbox() {
  return (
    <div className="relative shrink-0 size-[16px]" data-name="Checkbox">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid size-full" />
    </div>
  );
}

function Text() {
  return (
    <div className="basis-0 grow h-[20px] min-h-px min-w-px relative shrink-0" data-name="Text">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Arimo:Regular',sans-serif] font-normal leading-[20px] relative shrink-0 text-[#364153] text-[14px] text-nowrap whitespace-pre">Remember for 30 days</p>
      </div>
    </div>
  );
}

function Label() {
  return (
    <div className="h-[20px] relative shrink-0 w-[163.281px]" data-name="Label">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex gap-[8px] items-center relative size-full">
        <Checkbox />
        <Text />
      </div>
    </div>
  );
}

function Link() {
  return (
    <div className="h-[20px] relative shrink-0 w-[109.875px]" data-name="Link">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid content-stretch flex items-start relative size-full">
        <p className="font-['Arimo:Regular',sans-serif] font-normal leading-[20px] relative shrink-0 text-[#4a5565] text-[14px] text-nowrap whitespace-pre">Forgot password?</p>
      </div>
    </div>
  );
}

function Container() {
  return (
    <div className="absolute content-stretch flex h-[20px] items-center justify-between left-0 top-[250px] w-[448px]" data-name="Container">
      <Label />
      <Link />
    </div>
  );
}

function Button() {
  return (
    <div className="absolute bg-gradient-to-r from-[#ff8904] h-[48px] left-0 rounded-[3.35544e+07px] shadow-[0px_4px_6px_-1px_rgba(0,0,0,0.1),0px_2px_4px_-2px_rgba(0,0,0,0.1)] to-[#ff6900] top-[286px] w-[448px]" data-name="Button">
      <p className="absolute font-['Arimo:Regular',sans-serif] font-normal leading-[24px] left-[224.48px] text-[16px] text-center text-nowrap text-white top-[10px] translate-x-[-50%] whitespace-pre">Log In</p>
    </div>
  );
}

function Link1() {
  return (
    <div className="absolute content-stretch flex h-[19px] items-start left-[273.91px] top-0 w-[48.688px]" data-name="Link">
      <p className="font-['Arimo:Regular',sans-serif] font-normal leading-[20px] relative shrink-0 text-[#101828] text-[14px] text-center text-nowrap whitespace-pre">Sign Up</p>
    </div>
  );
}

function Paragraph() {
  return (
    <div className="absolute h-[20px] left-0 top-[374px] w-[448px]" data-name="Paragraph">
      <p className="absolute font-['Arimo:Regular',sans-serif] font-normal leading-[20px] left-[199.91px] text-[#4a5565] text-[14px] text-center top-[-2px] translate-x-[-50%] w-[149px]">{`Don't have an account?`}</p>
      <Link1 />
    </div>
  );
}

function EmailInput() {
  return (
    <div className="absolute h-[50px] left-0 rounded-[3.35544e+07px] top-[118px] w-[448px]" data-name="Email Input">
      <div className="content-stretch flex items-center overflow-clip px-[24px] py-[12px] relative rounded-[inherit] size-full">
        <p className="font-['Arimo:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[16px] text-[rgba(10,10,10,0.5)] text-nowrap whitespace-pre">Email</p>
      </div>
      <div aria-hidden="true" className="absolute border border-[#d1d5dc] border-solid inset-0 pointer-events-none rounded-[3.35544e+07px]" />
    </div>
  );
}

function PasswordInput() {
  return (
    <div className="absolute h-[50px] left-0 rounded-[3.35544e+07px] top-0 w-[448px]" data-name="Password Input">
      <div className="content-stretch flex items-center overflow-clip px-[24px] py-[12px] relative rounded-[inherit] size-full">
        <p className="font-['Arimo:Regular',sans-serif] font-normal leading-[normal] relative shrink-0 text-[16px] text-[rgba(10,10,10,0.5)] text-nowrap whitespace-pre">cfggggd</p>
      </div>
      <div aria-hidden="true" className="absolute border border-[#d1d5dc] border-solid inset-0 pointer-events-none rounded-[3.35544e+07px]" />
    </div>
  );
}

function Icon() {
  return (
    <div className="h-[20px] overflow-clip relative shrink-0 w-full" data-name="Icon">
      <div className="absolute inset-[20.84%_8.33%]" data-name="Vector">
        <div className="absolute inset-[-7.14%_-5%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 19 14">
            <path d={svgPaths.pcb0000} id="Vector" stroke="var(--stroke-0, #99A1AF)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" />
          </svg>
        </div>
      </div>
      <div className="absolute inset-[37.5%]" data-name="Vector">
        <div className="absolute inset-[-16.67%]">
          <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 7 7">
            <path d={svgPaths.p2314a170} id="Vector" stroke="var(--stroke-0, #99A1AF)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.66667" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function Button1() {
  return (
    <div className="absolute content-stretch flex flex-col items-start left-[404px] size-[20px] top-[15px]" data-name="Button">
      <Icon />
    </div>
  );
}

function Container1() {
  return (
    <div className="absolute h-[50px] left-0 top-[184px] w-[448px]" data-name="Container">
      <PasswordInput />
      <Button1 />
    </div>
  );
}

function Heading() {
  return (
    <div className="absolute h-[24px] left-[-3px] top-[18.51px] w-[448px]" data-name="Heading 1">
      <p className="absolute font-['Arimo:Bold',sans-serif] font-bold leading-[24px] left-0 text-[24px] text-neutral-950 text-nowrap top-[-2px] whitespace-pre">Lunch Voter</p>
    </div>
  );
}

function Form() {
  return (
    <div className="h-[265px] relative shrink-0 w-full" data-name="Form">
      <Container />
      <Button />
      <Paragraph />
      <EmailInput />
      <Container1 />
      <Heading />
    </div>
  );
}

function Paragraph1() {
  return (
    <div className="absolute h-[24px] left-0 top-[50px] w-[448px]" data-name="Paragraph">
      <p className="absolute font-['Arimo:Regular',sans-serif] font-normal leading-[24px] left-0 text-[#4a5565] text-[16px] text-nowrap top-[-2px] whitespace-pre">Vote with your team to decide where to eat</p>
    </div>
  );
}

function Container2() {
  return (
    <div className="absolute content-stretch flex flex-col gap-[8px] h-[482px] items-start left-[64px] top-[53.13px] w-[448px]" data-name="Container">
      <Form />
      <Paragraph1 />
    </div>
  );
}

function ImageDeliciousFood() {
  return <div className="absolute h-[588.266px] left-0 top-0 w-[576px]" data-name="Image (Delicious food)" />;
}

function Container3() {
  return (
    <div className="absolute h-[588.266px] left-0 top-0 w-[576px]" data-name="Container">
      <Image alt="" className="absolute inset-0 max-w-none object-50%-50% object-cover pointer-events-none size-full" src={imgContainer} />
    </div>
  );
}

function Container4() {
  return (
    <div className="absolute h-[588.266px] left-[576px] overflow-clip top-0 w-[576px]" data-name="Container">
      <ImageDeliciousFood />
      <Container3 />
    </div>
  );
}

function Container5() {
  return (
    <div className="bg-white h-[588.266px] relative rounded-[24px] shadow-[21px_25px_50px_-12px_#fef7ed] shrink-0 w-[1152px]" data-name="Container">
      <div className="bg-clip-padding border-0 border-[transparent] border-solid overflow-clip relative rounded-[inherit] size-full">
        <Container2 />
        <Container4 />
      </div>
    </div>
  );
}

export default function CreateLoginFlow() {
  return (
    <div className="content-stretch flex items-center justify-center relative size-full" data-name="Create Login Flow" style={{ backgroundImage: "linear-gradient(150.923deg, rgb(255, 247, 237) 0%, rgb(254, 242, 242) 100%)" }}>
      <Container5 />
    </div>
  );
}