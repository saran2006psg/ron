import React, {useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";

type Job = {job_id:string,status:string,progress:number,error?:{message:string},warnings:string[],result_links:Record<string,string>};
const api = import.meta.env.VITE_API_URL || "http://localhost:8000";
function App() {
 const [script,setScript]=useState(""); const [ratio,setRatio]=useState("16:9"); const [job,setJob]=useState<Job|null>(null); const [busy,setBusy]=useState(false); const [message,setMessage]=useState("");
 async function submit(e:React.FormEvent) { e.preventDefault(); if(!script.trim()){setMessage("Enter narration text.");return} setBusy(true);setMessage("");
  try { const r=await fetch(api+"/api/v1/broll/jobs",{method:"POST",headers:{"Content-Type":"application/json","Idempotency-Key":crypto.randomUUID()},body:JSON.stringify({script,aspect_ratios:[ratio],captions:{burn_in:true,srt:true}})}); const body=await r.json(); if(!r.ok) throw new Error(body.error?.message||"Submission failed"); setJob({...body,progress:0,warnings:[],result_links:{}}); poll(body.job_id); } catch(e){setMessage(e instanceof Error?e.message:"Network error");setBusy(false)} }
 function poll(id:string){const timer=window.setInterval(async()=>{try {const r=await fetch(api+"/api/v1/jobs/"+id);const next=await r.json();setJob(next);if(["succeeded","failed"].includes(next.status)){clearInterval(timer);setBusy(false)}}catch{clearInterval(timer);setBusy(false);setMessage("Lost connection while checking job")}},1000)}
 return <main><h1>IncuBrix B-roll Engine</h1><p>Submit narration and track its real backend job status.</p><form onSubmit={submit}><label>Narration<textarea value={script} onChange={e=>setScript(e.target.value)} placeholder="Write your voiceover…"/></label><label>Aspect ratio<select value={ratio} onChange={e=>setRatio(e.target.value)}><option>16:9</option><option>9:16</option><option>1:1</option></select></label><button disabled={busy}>{busy?"Processing…":"Create video"}</button></form>{message&&<p className="error">{message}</p>}{job&&<section><h2>{job.status} - {job.progress}%</h2>{job.error&&<p className="error">{job.error.message}</p>}{job.warnings.map(x=><p key={x}>{x}</p>)}</section>}</main> }
createRoot(document.getElementById("root")!).render(<App/>);

