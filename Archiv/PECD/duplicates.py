import pandas as pd

# Sample data, assuming it has been read into a DataFrame 'df' with columns 'Price_zone', 'Shape', and 'PP_ID'
# For illustration purposes, let's create it manually here.

# Load data
data = {
    "Price_zone": ["DE", "BT", "TR", "BA", "FR", "BE", "AT", "CH", "NL", "PL", "CZ", "DKW1", "DKE2", "SC", "SE01", "ITCN", "UK", "ITN1", "ES", "ES",
                   "RO", "SK", "HU", "BG", "GR", "PT", "NO", "FI", "ITCS", "SE03", "SE04", "ITS1", "ITSI", "ITSA", "ITCA", "DE", "BT", "TR", "BA", "FR",
                   "BE", "AT", "CH", "NL", "PL", "CZ", "DKW1", "DKE2", "SC", "SE01", "ITCN", "UK", "ITN1", "ES", "RO", "SK", "HU", "BG", "GR", "PT",
                   "NO", "FI", "ITCS", "SE03", "SE04", "ITSI", "ITS1", "ITSA", "ITCA", "ITCN", "ITN1", "ITCS", "ITS1", "ITSI", "ITSA", "ITCA", "DE", "BT",
                   "TR", "BA", "FR", "BE", "AT", "CH", "NL", "PL", "CZ", "DKW1", "DKE2", "SC", "SE01", "UK", "ES", "RO", "SK", "HU", "BG", "GR", "PT",
                   "NO", "FI", "SE03", "SE04", "DE", "FR", "BE", "NL", "DKW1", "DKE2", "UK", "SE04", "SE03", "PL", "DE", "UK", "FI", "BT", "NO", "ES",
                   "PT", "ITSA", "ITSI"],
    "Shape": ["B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B",
              "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "A", "A", "A", "A", "A", "A",
              "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A", "A",
              "A", "A", "A", "A", "A", "A", "A", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B",
              "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "B", "A", "A", "A", "A", "A", "A",
              "A", "A", "A", "A", "B", "B", "A", "A", "A", "A", "A", "A"],
    "PP_ID": [4832, 4866, 4851, 4857, 4823, 4802, 4819, 4806, 4855, 4878, 4817, 4824, 4827, 4848, 4845, 3678, 4861,
              4865, 4805, 4803, 4809, 4833, 4872, 4797, 4838, 4812, 4869, 4875, 3295, 4839, 4843, 3675, 4863, 2923,
              663, 4748, 4782, 4767, 4773, 4739, 4716, 4734, 4722, 4770, 4796, 4731, 4740, 4743, 4764, 4761, 4715,
              4776, 4781, 4721, 4725, 4749, 4788, 4713, 4752, 4730, 4785, 4791, 4719, 4755, 4758, 4723, 4726, 4728,
              679, 4718, 4714, 4720, 4724, 4727, 4729, 1289, 4732, 4733, 4735, 4736, 4737, 4742, 4745, 4747, 4750,
              4751, 4753, 4754, 4756, 4760, 4762, 4763, 4765, 4766, 4768, 4769, 4772, 4774, 4775, 4778, 4779, 4780,
              4783, 4746, 4738, 4717, 4771, 4741, 4744, 4777, 4759, 4757, 4794, 4784, 4786, 64, 275, 1639, 955, 1830,
              1646, 1642]
}

# Creating DataFrame
df = pd.DataFrame(data)

# Count unique PP_IDs
unique_pp_ids = df["PP_ID"].nunique()
print(f"Total unique PP_ID entries: {unique_pp_ids}")

# Generate dictionary with file names based on Shape
dictionnary = {}
for index, row in df.iterrows():
    pp_id = row["PP_ID"]
    shape_suffix = "_shape_a" if row["Shape"] == "A" else ""
    dictionnary[pp_id] = f"{row['Price_zone'].lower()}_2033_{row['Price_zone'].lower()}{shape_suffix}"

# Show dictionary and count
print(f"Generated dictionary has {len(dictionnary)} entries")
print(dictionnary)
