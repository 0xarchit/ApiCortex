import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-2xl bg-[#242938]/50 flex items-center justify-center mb-4">
        <Icon className="w-7 h-7 text-[#5B5DFF]/60" />
      </div>
      <h3 className="text-lg font-medium text-[#E6EAF2] mb-2">{title}</h3>
      <p className="text-[#9AA3B2] text-sm max-w-md">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}