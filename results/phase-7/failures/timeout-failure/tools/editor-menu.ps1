param([long]$Window=132166,[int]$Command=-1)
# Provenance: written during Phase 0 (issue #1) to post World Editor menu commands;
# moved from local/ in Phase 1 because tools/we_author.py uses it.
$ErrorActionPreference='Stop'
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class EditorNative {
 [DllImport("user32.dll")] public static extern IntPtr GetMenu(IntPtr hwnd);
 [DllImport("user32.dll")] public static extern IntPtr GetSubMenu(IntPtr menu,int pos);
 [DllImport("user32.dll")] public static extern int GetMenuItemCount(IntPtr menu);
 [DllImport("user32.dll")] public static extern uint GetMenuItemID(IntPtr menu,int pos);
 [DllImport("user32.dll",CharSet=CharSet.Unicode)] public static extern int GetMenuString(IntPtr menu,uint pos,StringBuilder text,int max,uint flags);
 [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd,uint msg,IntPtr wp,IntPtr lp);
}
'@
if ($Command -ge 0) {
 if (-not [EditorNative]::PostMessage([IntPtr]$Window,0x111,[IntPtr]$Command,[IntPtr]::Zero)) {throw 'PostMessage failed'}
 "Posted menu command $Command"
 exit 0
}
function Read-Menu([IntPtr]$Menu,[string]$Prefix) {
 for($i=0;$i -lt [EditorNative]::GetMenuItemCount($Menu);$i++) {
  $s=New-Object Text.StringBuilder 512
  [void][EditorNative]::GetMenuString($Menu,$i,$s,512,0x400)
  $label=$s.ToString(); $sub=[EditorNative]::GetSubMenu($Menu,$i)
  if($label) {"$Prefix$label -> $([EditorNative]::GetMenuItemID($Menu,$i))"}
  if($sub -ne [IntPtr]::Zero) {Read-Menu $sub "$Prefix$label / "}
 }
}
Read-Menu ([EditorNative]::GetMenu([IntPtr]$Window)) ''
