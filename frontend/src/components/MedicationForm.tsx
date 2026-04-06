import { FormEvent, useState } from "react";

type Props = {
  onSubmit: (payload: {
    medications: string[];
    patient: {
      age?: number;
      weight_kg?: number;
      liver_function?: string;
      renal_function?: string;
      conditions: string[];
    };
  }) => Promise<void>;
};

export function MedicationForm({ onSubmit }: Props) {
  const [medications, setMedications] = useState("Warfarin, Ibuprofen");
  const [age, setAge] = useState("74");
  const [weight, setWeight] = useState("48");
  const [conditions, setConditions] = useState("diabetes");
  const [liverFunction, setLiverFunction] = useState("reduced");
  const [renalFunction, setRenalFunction] = useState("impaired");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await onSubmit({
      medications: medications.split(",").map((item) => item.trim()).filter(Boolean),
      patient: {
        age: age ? Number(age) : undefined,
        weight_kg: weight ? Number(weight) : undefined,
        liver_function: liverFunction || undefined,
        renal_function: renalFunction || undefined,
        conditions: conditions.split(",").map((item) => item.trim()).filter(Boolean)
      }
    });
  }

  return (
    <form className="panel form-grid" onSubmit={handleSubmit}>
      <div className="panel-header">
        <p className="eyebrow">Clinical Input</p>
        <h2>Tell us the medicines</h2>
      </div>

      <label>
        Medicine names or medication IDs
        <textarea
          value={medications}
          onChange={(event) => setMedications(event.target.value)}
          rows={3}
        />
      </label>
      <p>Examples: Warfarin, Metformin, Ibuprofen, DB00945</p>

      <div className="two-up">
        <label>
          Age
          <input value={age} onChange={(event) => setAge(event.target.value)} />
        </label>
        <label>
          Weight (kg)
          <input value={weight} onChange={(event) => setWeight(event.target.value)} />
        </label>
      </div>

      <div className="two-up">
        <label>
          Liver function
          <input value={liverFunction} onChange={(event) => setLiverFunction(event.target.value)} />
        </label>
        <label>
          Renal function
          <input value={renalFunction} onChange={(event) => setRenalFunction(event.target.value)} />
        </label>
      </div>

      <label>
        Conditions
        <input value={conditions} onChange={(event) => setConditions(event.target.value)} />
      </label>

      <button type="submit">Check Interactions</button>
    </form>
  );
}
